# Order Processing and SellerCloud Integration

This project automates order processing, tax calculation, and integration with SellerCloud.

## Features
- Retrieves orders from the database and processes them.
- Validates SKUs and calculates tax rates.
- Creates and updates orders in SellerCloud.
- Rounds decimal values for financial accuracy.
- Sends email notifications for errors and order updates.

## Project Structure
```
project_root/
├── config.py              # Configuration file for database, API, and email credentials
├── decimal_rounding.py    # Handles rounding of decimal values
├── email_helper.py        # Sends email notifications
├── example_db.py          # Manages database interactions
├── main.py                # Main script orchestrating the order processing
├── order_creator.py       # Creates order objects and processes them
├── sales_tax_api.py       # Fetches tax rates from Zip-Tax API
├── seller_cloud_api.py    # Interfaces with SellerCloud API
```

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/order-processing.git
cd order-processing
```

### 2. Install Dependencies
Ensure you have Python 3 installed, then install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure the System
Modify `config.py` with your database, FTP, and API credentials.

Example database configuration:
```python
db_config = {
    "ExampleDb": {
        "server": "your.database.windows.net",
        "database": "YourDB",
        "username": "your_user",
        "password": "your_password",
        "driver": "{ODBC Driver 17 for SQL Server}",
    },
}
```
Example email configuration:
```python
SENDER_EMAIL = "your_email@example.com"
SENDER_PASSWORD = "your_email_password"
```

## Usage
Run the main script to start the process:
```bash
python main.py
```

## How It Works
1. Fetches orders from the database.
2. Validates and processes SKUs.
3. Calculates tax rates via the Zip-Tax API.
4. Creates and updates orders in SellerCloud.
5. Sends email notifications for errors or missing data.

## Tech Stack
- Python 3
- Azure SQL Database (`pyodbc`)
- SellerCloud API Integration
- Zip-Tax API for tax calculations
- Email Notifications (`smtplib`)
- Decimal rounding for financial accuracy

## Troubleshooting
- If you encounter database connection issues, ensure `ODBC Driver 17` is installed.
- If emails fail to send, ensure your SMTP settings allow external authentication.
- Verify SellerCloud credentials if API requests fail.
