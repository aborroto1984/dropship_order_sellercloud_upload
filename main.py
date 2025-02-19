from email_helper import send_email
from order_creator import OrderCreator
from example_db import ExampleDb
from seller_cloud_api import SellerCloudAPI
import traceback


def batches_creator(objects, batch_size):
    """Creates batches of objects to be processed."""
    counter = 1
    container = []
    try:
        # It makes batches of 50 skus to send to SellerCloud
        while True:
            if len(objects) > batch_size:
                batch = [objects.pop() for _ in range(batch_size)]
            else:
                batch = objects
                objects = []

            container.append(batch)

            if not objects:
                print(f"Done creating batches of {batch_size}.")
                return container

            counter += 1

    except Exception as e:
        print(f"Error creating batches: {e}")
        raise Exception(f"Error creating batches: {e}")


def main():
    try:
        ex_db = ExampleDb()

        # Getting inventory and sku_alias_set
        sku_shipping_map = ex_db.get_sku_alias_list()

        # The skus in batch are all the skus that are in the orders that is being processed
        # This is used to check if the skus are in SellerCloud using less API calls
        po_objects, skus_in_batch = ex_db.load_purchase_orders_not_in_sellercloud()

        sc_api = SellerCloudAPI()
        creator = OrderCreator(sc_api, skus_in_batch)

        # Getting the dropshippers information from SellerCloud
        for id, orders in po_objects.items():
            response = sc_api.execute(
                {"url_args": {"customer_id": id}}, "GET_CUSTOMERS_BY_ID"
            )
            customer = response.json()
            for order in orders:
                order["customer"] = customer

        # Exiting if there are no orders to upload
        if not po_objects:
            print("No orders to upload.")
            return

        for sellercloud_id, orders in po_objects.items():
            # List of orders that are in SellerCloud and ready to be updated in the database
            orders_in_sc_not_in_db = {}

            # Batch of orders to be uploaded to SellerCloud, this is to avoid uploading too many orders at once
            batches = batches_creator(orders, 50)

            for orders in batches:
                for order in orders[:]:
                    # Since the order is a copy of the original order, we need to get the index of the original order
                    index = orders.index(order)

                    # Creating the order object to be uploaded to SellerCloud
                    order_obj, order_amounts = creator.create_order(
                        order, sellercloud_id, sku_shipping_map
                    )

                    # Adding the order_amounts to the order object
                    orders[index]["order_amounts"] = order_amounts

                    # If there are no valid skus, skips the order. Report email was sent in create_order.
                    if not order_obj:
                        orders.pop(index)
                        continue

                    # Adding the order to SellerCloud
                    response = sc_api.execute(order_obj, "CREATE_ORDER")

                    # If the order is in SellerCloud, it is added to the list of orders ready to be updated in the database
                    if (
                        response.status_code == 500
                        and "already exists" in response.text
                    ):
                        # Saving a reference of the duplicate order to get the sellercloud_id later
                        orders_in_sc_not_in_db[
                            order_obj["OrderDetails"]["OrderSourceOrderID"]
                        ] = index
                        print("Order already in SellerCloud")

                    elif response.status_code == 200:
                        # Adding the sellercloud_id to the order object
                        orders[index]["sellercloud_order_id"] = response.json()
                        print(
                            f"Order uploaded: {order_obj['OrderDetails']['OrderSourceOrderID']}"
                        )

                    else:
                        unable_to_be_added = orders.pop(index)
                        send_email(
                            "There was an error uploading an order to SellerCloud",
                            f"Order: {unable_to_be_added}\n\nError: {response.text}",
                        )

                # Getting the sellercloud_ids for the orders that are in SellerCloud but not in the database
                if orders_in_sc_not_in_db:

                    # NOTE: This is not the sellercloud_order_ids but the OrderSourceOrderIDs
                    order_ids = list(orders_in_sc_not_in_db.keys())

                    response = sc_api.execute(
                        {
                            "url_args": {
                                "order_ids": " ,".join(order_ids),
                            }
                        },
                        "GET_SELLERCLOUD_IDS",
                    )

                    if response.status_code == 200:
                        for order in response.json()["Items"]:

                            # Getting the index of the original order
                            index = orders_in_sc_not_in_db[order["OrderSourceOrderID"]]

                            # Adding the sellercloud_id to the order
                            orders[index]["sellercloud_order_id"] = order["ID"]

                    else:
                        send_email(
                            "There was an error getting the sellercloud_ids from SellerCloud",
                            f"Error: \n{response.text}\nOrder IDs: \n{order_ids}",
                        )

                    orders_in_sc_not_in_db.clear()

                if orders:
                    # Updating the database
                    ex_db.updating_order_data_in_db(orders)

        ex_db.close()

    except Exception as e:
        if ex_db:
            ex_db.close()
        print(f"There was an error: {e}")
        send_email("An Error Occurred", f"Error: {e}\n\n{traceback.format_exc()}")
        raise e


if __name__ == "__main__":
    main()
