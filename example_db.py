from email_helper import send_email
from collections import defaultdict
from datetime import datetime
import pyodbc
from config import create_connection_string, db_config


class ExampleDb:
    def __init__(self):
        try:
            """Establishes a connection to the Example database"""

            self.conn = pyodbc.connect(create_connection_string(db_config["ExampleDb"]))
            self.cursor = self.conn.cursor()

        except pyodbc.Error as e:
            print(f"Error establishing connection to the ExampleDb database: {e}")
            raise

    def update_cancelled_status(self, order):
        """Updates the is_cancelled status of the purchase order"""

        try:
            self.cursor.execute(
                """
                UPDATE PurchaseOrders
                SET is_cancelled = 1
                WHERE purchase_order_number = ?
                """,
                order["purchase_order_number"],
            )

            self.conn.commit()
            print(
                f"Order {order['purchase_order_number']} was cancelled in ExampleDb database."
            )

        except Exception as e:
            print(f"Error while updating is_cancelled status: {e}")
            send_email(
                "There was an error cancelling the following purchase orders in the database: ",
                f"{order}",
            )

    def load_purchase_orders_not_in_sellercloud(self):
        """Loads the purchase orders that are not in SellerCloud"""

        try:
            # Inserting into PurchaseOrders
            self.cursor.execute(
                """
                SELECT
                    d.sellercloud_customer_id,
                    d.code as dropshipper_code,
                    po.id,
                    po.purchase_order_number,
                    po.date_added,
                    po.customer_first_name,
                    po.customer_last_name,
                    po.phone,
                    po.address,
                    po.city,
                    s.name as state,
                    po.zip,
                    c.two_letter_code as country,
                    po.dropshipper_id,
                    te.is_exempt,
                    d.company_shipping_account as ships_with_company_account,
                    d.ship_method
                FROM PurchaseOrders po
                JOIN Dropshippers d ON po.dropshipper_id = d.id
                JOIN States s ON po.state = s.id
                JOIN Countries c ON po.country = c.id
                JOIN TaxExempt te ON po.dropshipper_id = te.dropshipper_id AND po.state = te.state_id
                WHERE po.in_sellercloud = 0 AND po.is_cancelled = 0 AND d.code != 'ABS' AND po.date_added > '2024-01-01'
                """
            )
            # Getting the purchase orders data
            rows = self.cursor.fetchall()

            # Getting the column names to use as keys
            columns = [col[0] for col in self.cursor.description]

            #  Creating object with the purchase orders data
            po_objects = [dict(zip(columns, row)) for row in rows]

            # Sorting the purchase orders by dropshipper_sellercloud_id
            orders_by_dropshipper = {}
            skus_in_batch = []

            for po in po_objects:
                # Getting the purchase order items
                self.cursor.execute(
                    """
                    SELECT
                        sku,
                        quantity
                    FROM PurchaseOrderItems
                    WHERE purchase_order_id = ?
                    """,
                    po["id"],
                )
                # Getting the purchase order items data
                rows = self.cursor.fetchall()
                # Getting the column names to use as keys
                columns = [col[0] for col in self.cursor.description]

                # Creating object with the purchase order items data and a list of skus
                po_items = []

                for row in rows:
                    po_items.append(dict(zip(columns, row)))
                    skus_in_batch.append(row[0])

                # Adding the purchase order items to the purchase order object
                po["items"] = po_items

                # Get the dropshipper_sellercloud_id from the current object
                sellercloud_customer_id = po["sellercloud_customer_id"]

                # If this sellercloud_customer_id is not in the dictionary, add it with an empty list
                if not orders_by_dropshipper.get(sellercloud_customer_id):
                    orders_by_dropshipper[sellercloud_customer_id] = []

                # Append the current purchase order object to the list of this sellercloud_customer_id
                orders_by_dropshipper[sellercloud_customer_id].append(po)

            return orders_by_dropshipper, skus_in_batch

        except Exception as e:
            print(f"Error while storing purchase orders: {e}")
            raise

    def updating_order_data_in_db(self, orders):
        """Updates the in_sellercloud status of the purchase order"""

        if not self.conn and self.conn.closed:
            self.conn = pyodbc.connect(create_connection_string(db_config["ExampleDb"]))
            self.cursor = self.conn.cursor()

        curr_time = datetime.now()

        purchase_orders_data = []

        for order in orders:
            purchase_orders_data.append(
                (
                    curr_time,
                    order["sellercloud_order_id"],
                    order["order_amounts"]["shipping_total"],
                    order["purchase_order_number"],
                )
            )

        try:
            # Execute bulk update for PurchaseOrders
            self.cursor.executemany(
                """
                UPDATE PurchaseOrders
                SET in_sellercloud = 1, in_sellercloud_date = ?, sellercloud_order_id = ?, shipping_cost = ?
                WHERE purchase_order_number = ?
                """,
                purchase_orders_data,
            )

            self.conn.commit()

        except Exception as e:
            print(f"Error while updating in_sellercloud status: {e}")
            send_email(
                "There was an error updating the following purchase orders in the database after being added to SellerCloud: ",
                f"{orders}",
            )

    def get_sku_alias_list(self):
        """Gets a list of skus and aliases from the database"""
        try:
            self.cursor.execute(
                """
                SELECT
                    sku,
                    alias,
                    shipping_cost
                FROM vProductAndAliases
                """
            )
            rows = self.cursor.fetchall()

            # Place holder for the sku and alias set
            sku_alias_map = defaultdict(list)

            # Place holder for the sku and shipping cost set
            sku_shipping_map = {}

            for sku, alias, shipping_cost in rows:
                if not alias:
                    sku_alias_map[sku].append(None)
                else:
                    sku_alias_map[sku].append(alias)

                # Storing the shipping cost for each sku and alias
                if not sku_shipping_map.get(sku):
                    sku_shipping_map[sku] = shipping_cost
                if not sku_shipping_map.get(alias):
                    sku_shipping_map[alias] = shipping_cost

            return sku_shipping_map

        except Exception as e:
            print(f"Error while getting skus and aliases: {e}")
            raise

    def get_sellercloud_order_ids(self, purchase_order_numbers=None):
        """Gets the sellercloud order ids for the purchase order numbers"""
        try:
            if purchase_order_numbers:
                placeholders = ", ".join("?" for _ in purchase_order_numbers)
                self.cursor.execute(
                    f"""
                    SELECT
                        sellercloud_order_id,
                    FROM PurchaseOrders
                    WHERE purchase_order_number in ({placeholders})
                    """,
                    purchase_order_numbers,
                )
                rows = self.cursor.fetchall()
                columns = [col[0] for col in self.cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            else:
                self.cursor.execute(
                    """
                    SELECT
                        sellercloud_order_id
                    FROM PurchaseOrders
                    WHERE sellercloud_order_id IS NOT NULL 
                    """
                )
                rows = self.cursor.fetchall()

                return [row[0] for row in rows]

        except Exception as e:
            print(f"Error while getting sellercloud order ids: {e}")
            raise

    def close(self):
        self.cursor.close()
        self.conn.close()
