from seller_cloud_api import SellerCloudAPI
from config import zip_tax_api_key
from sales_tax_api import SalesTaxApi
from email_helper import send_missing_parts_error_report, send_email
from decimal_rounding import round_to_decimal


class OrderCreator:
    def __init__(self, sc_api: SellerCloudAPI, skus_in_batch):
        self.sc_api = sc_api
        self.t_api = SalesTaxApi(zip_tax_api_key)
        self.skus_in_sellercloud = self._get_skus_in_sellercloud(skus_in_batch)

    def create_order(self, order, sellercloud_id, sku_shipping_map):
        """Create order objects for SellerCloud and get the order totals."""
        dropshipper_name = order["customer"]["General"]["Name"]
        dropshipper_discount = order["customer"]["OrderOptions"]["WholesaleDiscount"]
        dropshipper_email = order["customer"]["General"]["Email"]

        # Making sure the skus are in SellerCloud
        skus = self._validate_skus(
            order["items"], order["purchase_order_number"], dropshipper_name
        )

        # If there are no valid skus, skips the order
        if not skus:
            return None, None

        # Formatting the skus to be used in the order object and getting the order's total_price
        products, order_amounts = self._create_skus(
            skus,
            sku_shipping_map,
            order["zip"],
            order["is_exempt"],
            order["ships_with_company_account"],
            dropshipper_discount,
            order["purchase_order_number"],
        )

        if products:
            # Creating the order id reference
            code_length = len(order["dropshipper_code"])

            if (
                order["purchase_order_number"][:code_length]
                == order["dropshipper_code"]
            ):
                order_id = order["purchase_order_number"]
            else:
                order_id = order["dropshipper_code"] + order["purchase_order_number"]

            # Preparing shipping details
            if order["ship_method"] == "UPS Ground":
                shipping_details = {
                    "ShippingMethod": "UPSGround",
                    "Carrier": "UPS",
                    "ShippingFee": order_amounts["shipping_total"],
                    "AllowShippingEvenNotPaid": True,
                }
            elif order["ship_method"] == "FEDEX Ground HD":
                shipping_details = {
                    "ShippingMethod": "FedExGround",
                    "Carrier": "Fedex",
                    "ShippingFee": order_amounts["shipping_total"],
                    "AllowShippingEvenNotPaid": True,
                }

            # Creating the order objects
            order_obj = {
                "CustomerDetails": {
                    "ID": sellercloud_id,
                    "Email": dropshipper_email,
                    "FirstName": dropshipper_name,
                    "Business": dropshipper_name,
                    "IsWholesale": True,
                },
                "OrderDetails": {
                    "CompanyID": 1,  # Placeholder
                    "TaxExempt": order["is_exempt"],
                    "Channel": 21,
                    "OrderSourceOrderID": order_id,
                    "OrderDate": order["date_added"].strftime("%Y-%m-%d %H:%M:%S"),
                },
                "Products": products,
                "ShippingAddress": {
                    "FirstName": order["customer_first_name"],
                    "LastName": order["customer_last_name"],
                    "Country": order["country"],
                    "City": order["city"],
                    "State": order["state"],
                    "ZipCode": order["zip"],
                    "Address": order["address"],
                    "Phone": order["phone"],
                },
                "ShippingMethodDetails": shipping_details,
            }

            return order_obj, order_amounts
        else:
            return None, None

    def _create_skus(
        self,
        skus,
        sku_shipping_map,
        ships_with_company_account,
        discount,
        purchase_order_number,
    ):
        """Adding the skus to the order object and getting the order totals."""
        shipping_total = 0

        sku_objs = []
        order_amounts = {"skus_prices": {}}

        for sku in skus:
            # Calculating shipping
            if ships_with_company_account:
                if sku["sku"] in sku_shipping_map:
                    sku_shipping_price = sku_shipping_map[sku["sku"]] * sku["quantity"]
                    shipping_total += sku_shipping_price
                else:
                    send_email(
                        "Error Calculating Shipping",
                        f"There was an error calculating shipping for order {purchase_order_number}, sku: {sku['sku']} was not found in the ProductCatalog database.",
                    )
                    return None, None
            else:
                shipping_total = 0

            # Adding the sku to the order object
            sku_objs.append(
                {
                    "ProductID": sku["sku"],
                    "Qty": sku["quantity"],
                    "DiscountValue": discount,
                    "DiscountType": 1,
                }
            )

            # order_amounts["skus_prices"][sku["sku"]] = discounted_amount

        # Creating the order totals
        order_amounts["shipping_total"] = round_to_decimal(shipping_total)

        return sku_objs, order_amounts

    def _validate_skus(self, skus, purchase_order_number, dropshipper_name):
        """Makes sure the skus are in SellerCloud and returns the prices."""

        # Placeholder for the valid and invalid skus
        valid_skus = []
        invalid_skus = []

        # Separating the valid and invalid skus
        for sku in skus:
            if (
                sku["sku"] in self.skus_in_sellercloud
                and self.skus_in_sellercloud[sku["sku"]] > 0
            ):
                valid_skus.append(
                    {
                        "sku": sku["sku"],
                        "quantity": sku["quantity"],
                        "unit_price": self.skus_in_sellercloud[sku["sku"]],
                    }
                )
            else:
                invalid_skus.append({"sku": sku["sku"], "quantity": sku["quantity"]})

        # Sending an email with the invalid skus
        if invalid_skus:
            skus_str = ""
            missing_price = False
            for sku in invalid_skus:
                if (
                    sku["sku"] in self.skus_in_sellercloud
                    and self.skus_in_sellercloud[sku["sku"]] <= 0
                ):
                    missing_price = True

                skus_str += f"{sku['sku']} - {sku['quantity']} units\n"

            send_missing_parts_error_report(
                skus_str, purchase_order_number, dropshipper_name, missing_price
            )

            return None

        return valid_skus

    def _get_skus_in_sellercloud(self, sku_numbers):
        """Checks to see if a batch of skus are in SellerCloud."""
        # NOTE: This only returns the skus that are in SellerCloud
        skus_in_sellercloud = {}
        try:
            # It makes batches of 50 skus to send to SellerCloud
            while True:
                if len(sku_numbers) > 50:
                    batch = [sku_numbers.pop() for _ in range(50)]
                else:
                    batch = sku_numbers
                    sku_numbers = []

                # Using the previously extracted skus to get the skus from SellerCloud
                check_sku_data = {"url_args": {"skus": ", ".join(batch)}}
                response = self.sc_api.execute(check_sku_data, "GET_SELLERCLOUD_SKUS")

                # Getting the skus and their prices from SellerCloud response
                if response and response.json():
                    for sku in response.json()["Items"]:
                        skus_in_sellercloud[sku["ID"]] = sku["WholeSalePrice"]

                if not sku_numbers:
                    return skus_in_sellercloud

        except Exception as e:
            print(f"Error getting skus from SellerCloud: {e}")
            raise Exception("Error getting skus from SellerCloud")


# order_model ------------------------------------------------------------------------------

# {
#   "ID": 0,
#   "CustomerDetails": {
#     "ID": 0,
#     "Email": "string",
#     "FirstName": "string",
#     "LastName": "string",
#     "Business": "string",
#     "IsWholesale": true,
#     "IgnoreCreditLimit": true
#   },
#   "OrderDetails": {
#     "CompanyID": 0,
#     "MarketingSource": 0,
#     "SalesRepresentative": 0,
#     "IsCurrencyVisible": true,
#     "CurrencyCode": 0,
#     "CurrencyRateFromUSD": 0,
#     "CurrencyRateToUSD": 0,
#     "TaxExempt": true,
#     "IsQuoteOrder": true,
#     "IsSampleOrder": true,
#     "GiftOrder": true,
#     "Channel": 0,
#     "OrderSourceOrderID": "string",
#     "DisableInventoryCount": true,
#     "OrderDate": "2024-01-18T15:58:19.011Z",
#     "EbaySellingManagerSalesRecordNumber": "string"
#   },
#   "GiftDetails": {
#     "UseGiftWrap": true,
#     "GiftMessage": "string",
#     "GiftWrap": 0,
#     "GiftWrapType": "string"
#   },
#   "Products": [
#     {
#       "ProductID": "string",
#       "ReferenceID": "string",
#       "ProductName": "string",
#       "SitePrice": 0,
#       "DiscountValue": 0,
#       "DiscountType": 0,
#       "Qty": 0,
#       "LineTaxTotal": 0,
#       "FinalValueFee": 0,
#       "Notes": "string",
#       "ShipFromWareHouseID": 0
#     }
#   ],
#   "ShippingAddress": {
#     "Business": "string",
#     "FirstName": "string",
#     "MiddleName": "string",
#     "LastName": "string",
#     "Country": "string",
#     "City": "string",
#     "State": "string",
#     "Region": "string",
#     "ZipCode": "string",
#     "Address": "string",
#     "Address2": "string",
#     "Phone": "string",
#     "Fax": "string"
#   },
#   "BillingAddress": {
#     "Business": "string",
#     "FirstName": "string",
#     "MiddleName": "string",
#     "LastName": "string",
#     "Country": "string",
#     "City": "string",
#     "State": "string",
#     "Region": "string",
#     "ZipCode": "string",
#     "Address": "string",
#     "Address2": "string",
#     "Phone": "string",
#     "Fax": "string"
#   },
#   "ShippingMethodDetails": {
#     "Carrier": "string",
#     "ShippingMethod": "string",
#     "Weight": {
#       "Pounds": 0,
#       "Ounces": 0
#     },
#     "Dimension": {
#       "Width": 0,
#       "Height": 0,
#       "Length": 0
#     },
#     "HandlingFee": 0,
#     "ShippingFee": 0,
#     "InsuranceFee": 0,
#     "LockShippingMethod": true,
#     "RushOrder": true,
#     "RequirePinToShip": true,
#     "OtherCarrier": "string",
#     "OtherMethod": "string",
#     "PromiseDate": "2024-01-18T15:58:19.011Z"
#   },
#   "Notes": [
#     {
#       "EntityID": 0,
#       "Category": 0,
#       "NoteID": 0,
#       "Note": "string",
#       "AuditDate": "2024-01-18T15:58:19.011Z",
#       "CreatedBy": 0,
#       "CreatedByName": "string",
#       "CreatedByEmail": "string"
#     }
#   ]
# }
