import requests
from requests.exceptions import HTTPError, Timeout, RequestException
from email_helper import send_email
from urllib.parse import quote
from config import sellercloud_credentials, sellercloud_endpoints


class SellerCloudAPI:
    """
    Class to handle requests to the Seller Cloud order managing API.
    It takes a dictionary with the credentials and a dictionary with the endpoints both from config.py.
    The endpoints dictionary should have the following structure:
    endpoints = {
        "EXAMPLE": {
        "type": "post", "get" or "delete",
        "url": the url of the endpoint with the placeholders for the url_args in the format {url_arg},
        "endpoint_error_message": the error message fragment to be displayed if the request fails in the format "while (the action it was performing): ",
        "success_message": the success message to be displayed if the request is successful in the format "(API name) (action it was performing) successfully!",
    },
    """

    def __init__(self):
        self.data = sellercloud_credentials
        self.endpoints = sellercloud_endpoints
        response = self.execute(self.data, "GET_TOKEN")
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def execute(self, data, action):
        """Executes a request to the SellerCloud API.
        Valid actions are: CREATE_ORDER, ADD_ITEM, GET_PRODUCT, GET_TOTAL, UPDATE_TAX, DELETE_ORDER.
        The data parameter should be a dictionary with the data to be sent to the API and the url_args to be used in the url in the format:
        data = {
            "url_args": {"url_arg1": "value1", "url_arg2": "value2"...},
            "data_key": "data_value"
            "data_key2": "data_value2"...,
        }
        The url_args are the values that will be used to replace the placeholders in the url like this: {url_arg1} -> value1
        url_exammple = "https://url_example.com/{url_arg1}/{url_arg2}"
        """
        config = self.endpoints.get(action)
        if not config:
            raise ValueError("Invalid API action")

        if action == "GET_TOKEN":
            self.headers = None
            return self.perform_request(self.data, **config)

        return self.perform_request(data, **config)

    def perform_request(
        self,
        data,
        type,
        url,
        endpoint_error_message,
        success_message,
    ):
        """Performs a request to the SellerCloud API."""
        error_message = None
        max_attempts = 3
        timeout = 1000

        for attempt in range(max_attempts):
            try:
                url_args = data.pop("url_args", None)

                if url_args:
                    formatted_url = self._sanitize_url(url, url_args)
                else:
                    formatted_url = url

                request_function = getattr(requests, type)

                response = request_function(
                    formatted_url, headers=self.headers, json=data, timeout=timeout
                )
                break
            except ConnectionError:
                if attempt < max_attempts - 1:
                    continue
                else:
                    error_message = (
                        f"Connection error occurred {endpoint_error_message}"
                    )
            except HTTPError as http_err:
                error_message = (
                    f"HTTP error occurred {endpoint_error_message}{http_err}"
                )
            except Timeout:
                error_message = f"Timeout occurred {endpoint_error_message}"
            except RequestException as err:
                error_message = f"Other error occurred {endpoint_error_message}{err}"
            except Exception as e:
                error_message = (
                    f"An unexpected error occurred {endpoint_error_message}{e}"
                )

        if error_message:
            print(error_message)
            send_email(
                "There was an error executing a request on SellerCloud API : ",
                error_message,
            )
            return None
        elif response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return response
        else:
            print(success_message)
            return response

    def _sanitize_url(self, url, url_args):
        """Constructs a URL for a  API request."""
        sanitized_url_args = {k: quote(str(v)) for k, v in url_args.items()}
        return url.format(**sanitized_url_args)
