import requests
from email_helper import send_email


class SalesTaxApi:
    def __init__(self, zip_tax_api_key):
        self.api_key = zip_tax_api_key

    def get_tax_rate(self, postalcode):
        if len(postalcode) > 5:
            postalcode = postalcode[:5]

        url = f"https://api.zip-tax.com/request/v40?key={self.api_key}&postalcode={postalcode}"
        max_attempts = 3
        timeout = 10

        for attempt in range(max_attempts):
            try:
                response = requests.get(url, timeout=timeout)

                return response.json()["results"][0]["taxSales"]
            except ConnectionError as e:
                if attempt < max_attempts - 1:
                    continue
                else:
                    send_email(
                        "Tax Calculation",
                        f"Error getting tax rate for {self.po}-{postalcode}\n\n{e}",
                    )
                return 0.0
            except Exception as e:
                send_email(
                    "Tax Calculation",
                    f"Error getting tax rate for {self.po}-{postalcode}\n\n{e}",
                )
                return 0.0
