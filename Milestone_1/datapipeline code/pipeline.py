import csv
import os
from datetime import datetime
import pandas as pd


class TransactionPipeline:
    def __init__(self, storage_dir='transactions', log_dir='logs'):
        self.storage_dir = storage_dir
        self.log_dir = log_dir
        self.log_file = os.path.join(self.log_dir, 'anonymization_log.csv')

        # check log directories exist
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Create the log file if doesn't exist
        if not os.path.isfile(self.log_file):
            with open(self.log_file, 'w', newline='') as logfile:
                log_writer = csv.writer(logfile)
                log_writer.writerow(['transaction_id', 'anonymization_timestamp', 'status'])

    def get_next_id(self, filepath):
        if not os.path.isfile(filepath):
            return 1
        with open(filepath, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)
            rows = list(reader)
            if not rows:
                return 1
            last_transaction_id = int(rows[-1][0])
            return last_transaction_id + 1

    def clean_data(self, products):
        # Convert NaN values to empty strings and remove it
        cleaned_products = [str(product) if not pd.isna(product) else '' for product in products]
        cleaned_products = [product for product in cleaned_products if product]
        return cleaned_products

    def log_anonymize(self, transaction_id, success=True):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = 'Success' if success else 'Failed'
        with open(self.log_file, 'a', newline='') as logfile:
            log_writer = csv.writer(logfile)
            log_writer.writerow([transaction_id, timestamp, status])
        # print(f"Transaction {transaction_id} anonymization {status} and logged at {timestamp}")

    def save_transaction(self, products):
        timestamp = datetime.now()
        filename = f"transaction_{timestamp.strftime('%Y-%m-%d')}.csv"
        filepath = os.path.join(self.storage_dir, filename)

        # Get next transaction ID
        transaction_id = self.get_next_id(filepath)

        # Data Preprocessing
        cleaned_products = self.clean_data(products)

        # Check if cleaned_products is empty
        if not cleaned_products:
            # print(f"Transaction {transaction_id} has no products to save.")
            return

        # Check if file exists
        file_exists = os.path.isfile(filepath)

        # save the transaction
        try:
            with open(filepath, 'a', newline='') as csvfile:
                fieldnames = ['transaction', 'products', 'datetime']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                transaction_data = {
                    'transaction': transaction_id,
                    'products': ', '.join(cleaned_products),
                    'datetime': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                writer.writerow(transaction_data)
            self.log_anonymize(transaction_id, success=True)
            # print(f"Transaction {transaction_id} saved to {filepath}")
        except Exception as e:
            # If saving fails, log will failed
            # print(f"Failed to save transaction {transaction_id}: {e}")
            self.log_anonymize(transaction_id, success=False)
