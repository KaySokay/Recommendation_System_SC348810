from datetime import datetime
import pandas as pd
from src.recommendation import get_db_connection

class TransactionPipeline:
    def __init__(self, retail_data_file='./data/retail-data.csv', chunk_size=10000):
        self.retail_data_file = retail_data_file
        self.chunk_size = chunk_size 
        
    def save_log(self, transaction_id, recommended_items, purchased_items):
        conn = get_db_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        recommended_str = ', '.join(recommended_items) if recommended_items else 'None'
        purchased_str = ', '.join(purchased_items) if purchased_items else 'None' 

        try:
            # Insert into recommendation_logs with transaction_id
            cursor.execute('''
                INSERT INTO recommendation_logs (transaction_id, recommended_items, purchased_items, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (transaction_id, recommended_str, purchased_str, timestamp))

            # Insert into transactions table
            cursor.execute('''
                INSERT INTO transactions (products, datetime)
                VALUES (?, ?)
            ''', (purchased_str, timestamp))

            # Insert into anonymization_logs table
            cursor.execute('''
                INSERT INTO anonymization_logs (Anonymization_Timestamp, Status)
                VALUES (?, ?)
            ''', (timestamp, 'Success'))

            conn.commit()
            print("Log saved successfully.")
        except Exception as e:
            conn.rollback()
            print(f"Failed to save log: {str(e)}")
        finally:
            conn.close()


    def log_anonymization(self, cursor, transaction_id, status):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = (transaction_id, timestamp, status)

        # Insert the log entry
        cursor.execute('''
            INSERT INTO anonymization_logs (Transaction_ID, Anonymization_Timestamp, Status)
            VALUES (?, ?, ?)
        ''', log_entry)
    
    def save_anonymized_transactions(self, df):
        # Saves anonymized transactions
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            grouped_df = df.groupby('Transaction_ID').agg({
                'Product_Name': lambda x: ', '.join(self.clean_data(x))
            }).reset_index()

            # Insert new transactions 
            for _, row in grouped_df.iterrows():
                product_names = row['Product_Name']
                transaction_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Insert the concatenated product names into the database
                cursor.execute('''
                    INSERT INTO transactions (products, datetime)
                    VALUES (?, ?)
                ''', (product_names, transaction_time))

                # Get the last inserted transaction ID
                cursor.execute("SELECT last_insert_rowid()")
                last_transaction_id = cursor.fetchone()[0]

                # Log anonymization success for the transaction
                self.log_anonymization(cursor, last_transaction_id, "Success")

            conn.commit()
            print(f"Successfully processed {len(grouped_df)} transactions.")
        except Exception as e:
            conn.rollback()
            print(f"Failed to insert transactions or logs: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def clean_data(self, products):
        # Cleans product data by converting NaN to empty strings and removing empty values.
        return [str(product) for product in products if pd.notna(product)]

    def anonymize_data(self, df):
        # Remove Customer_ID
        if 'Customer_ID' in df.columns:
            return df.drop(columns=['Customer_ID'], errors='ignore')
        return df

    def process_new_data(self):
        # Track the number of chunks processed
        chunk_count = 0

        # Read and process data in chunks
        for chunk in pd.read_csv(self.retail_data_file, chunksize=self.chunk_size):
            anonymized_chunk = self.anonymize_data(chunk)
            self.save_anonymized_transactions(anonymized_chunk)
            
            # Increment and log the chunk count
            chunk_count += 1
            print(f"Processed chunk {chunk_count}")

        print(f"Total chunks processed: {chunk_count}")
