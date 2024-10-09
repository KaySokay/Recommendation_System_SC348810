from datetime import datetime
import pandas as pd
from src.recommendation import get_db_connection 

class TransactionPipeline:
    def __init__(self, retail_data_file='./data/retail-data.csv'):
        self.retail_data_file = retail_data_file
        self.anonymization_logs = []

    def get_last_transaction_id(self):
        # Get the last transaction ID
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT MAX(transaction_id) FROM transactions")
            result = cursor.fetchone()
            return int(result[0]) if result[0] is not None else 0
        finally:
            conn.close()

    def log_anonymization(self, transaction_id, status, error_message=None):
        # Collect anonymization logs
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = (transaction_id, timestamp, status if not error_message else f"{status}: {error_message}")
        self.anonymization_logs.append(log_entry)

    def bulk_insert_anonymization_logs(self):
        if self.anonymization_logs:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.executemany('''
                    INSERT INTO anonymization_logs (Transaction_ID, Anonymization_Timestamp, Status)
                    VALUES (?, ?, ?)
                ''', self.anonymization_logs)
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Failed to insert anonymization logs: {e}")
            finally:
                cursor.close()
            self.anonymization_logs.clear()

    def clean_data(self, products):
        # Cleans product data by converting NaN to empty strings and removing empty values.
        return [str(product) for product in products if pd.notna(product)]

    def anonymize_data(self, df):
        # Remove Customer_ID
        return df.drop(columns=['Customer_ID'], errors='ignore') if 'Customer_ID' in df.columns else df

    def save_anonymized_transactions(self, df):
        # Saves anonymized transactions
        conn = get_db_connection()
        cursor = conn.cursor()

        transaction_id = self.get_last_transaction_id() + 1

        grouped_df = df.groupby('Transaction_ID').agg({
            'Product_Name': lambda x: ', '.join(self.clean_data(x))
        }).reset_index()

        transaction_data = [
            (transaction_id + i, row['Product_Name'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            for i, row in grouped_df.iterrows()
        ]

        try:
            cursor.executemany('''
                INSERT INTO transactions (transaction_id, products, datetime)
                VALUES (?, ?, ?)
            ''', transaction_data)
            conn.commit()
            # Log anonymization success
            for i in range(len(grouped_df)):
                self.log_anonymization(transaction_id + i, "Success")
        except Exception as e:
            # conn.rollback()
            print(f"Failed to insert transactions: {e}")
            # Log anonymization failure
            for i in range(len(grouped_df)):
                self.log_anonymization(transaction_id + i, "Failed", str(e))
        finally:
            cursor.close()

    def process_new_data(self, chunksize=10000):
        # Processes data from retail-data.csv
        for chunk in pd.read_csv(self.retail_data_file, chunksize=chunksize):
            anonymized_data = self.anonymize_data(chunk)
            self.save_anonymized_transactions(anonymized_data)

        # insert any remaining anonymization logs
        self.bulk_insert_anonymization_logs()
