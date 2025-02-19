db_config = {
    "ExampleDb": {
        "server": "example.database.windows.net",
        "database": "ExampleDb",
        "username": "example",
        "password": "example",
        "driver": "{ODBC Driver 17 for SQL Server}",
        "port": 1433,  # Default port for SQL Server
    },
}


def create_connection_string(server_config):
    return (
        f"DRIVER={server_config['driver']};"
        f"SERVER={server_config['server']};"
        f"PORT={server_config["port"]};DATABASE={server_config['database']};"
        f"UID={server_config['username']};"
        f"PWD={server_config['password']}"
    )


sellercloud_credentials = {
    "Username": "username",
    "Password": "password",
}

sellercloud_base_url = "https://example_company.api.sellercloud.us/rest/api/"

sellercloud_endpoints = {
    "CREATE_ORDER": {
        "type": "post",
        "url": sellercloud_base_url + "orders",
        "endpoint_error_message": "while creating order in SellerCloud: ",
        "success_message": "",
    },
    "GET_TOKEN": {
        "type": "post",
        "url": sellercloud_base_url + "token",
        "endpoint_error_message": "while getting SellerCoud API access token: ",
        "success_message": "Got SellerCloud API access token successfully!",
    },
    "GET_SELLERCLOUD_IDS": {
        "type": "get",
        "url": sellercloud_base_url
        + "Orders?model.orderSourceOrderIDList={order_ids}&model.pageSize=50",
        "endpoint_error_message": "while getting sellercloud_ids from SellerCloud: ",
        "success_message": "Got sellercloud_ids successfully!",
    },
    "GET_SELLERCLOUD_SKUS": {
        "type": "get",
        "url": sellercloud_base_url + "Catalog?model.sKU={skus}&model.pageSize=50",
        "endpoint_error_message": "while getting order skus from SellerCloud: ",
        "success_message": "Got all orders skus  from SellerCloud successfully!",
    },
    "DELETE_ORDER": {
        "type": "delete",
        "url": sellercloud_base_url + "Orders/{order_id}",
        "endpoint_error_message": "while deleting order in SellerCloud: ",
        "success_message": "SellerCloud deleted an order successfully!",
    },
    "GET_CUSTOMERS": {
        "type": "get",
        "url": sellercloud_base_url + "Customers?model.customerType=1",
        "endpoint_error_message": "while getting wholesale customers: ",
        "success_message": "Got customers successfully!",
    },
    "GET_CUSTOMERS_BY_ID": {
        "type": "get",
        "url": sellercloud_base_url + "Customers/{customer_id}",
        "endpoint_error_message": "while getting wholesale customers by id: ",
        "success_message": "Got customers successfully!",
    },
}

zip_tax_api_key = "zip_tax_api_key"
zip_tax_api_url = (
    "https://api.zip-tax.com/request/v40?key={api_key}&postalcode={postalcode}"
)

SENDER_EMAIL = "sender_email@domain.com"
SENDER_PASSWORD = "sender_password"
RECIPIENT_EMAILS = [
    "recipient_email_1@domain.com",
    "recipient_email_2@domain.com",
]  # List of emails to send the report
