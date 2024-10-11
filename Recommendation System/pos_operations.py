import pandas as pd
from datetime import datetime
import os
import csv

class POSOperations:
    def __init__(self, recommend_log_path='./logs/recommend_log.csv'):
        self.product_quantities = {}
        self.product_prices = {}
        self.total_price = 0.0
        self.transaction_counter = 0
        self.recommend_log_path = recommend_log_path

        # Load the transaction counter from the recommend_log file
        self.load_transaction_counter_from_log()

    def generate_transaction_id(self):
        # Increment the transaction
        self.transaction_counter += 1
        return f"REC00{self.transaction_counter:02d}"

    def load_transaction_counter_from_log(self):
        # Load value from the recommend_log file
        if os.path.exists(self.recommend_log_path):
            try:
                log_df = pd.read_csv(self.recommend_log_path)
                self.transaction_counter = len(log_df)
            except Exception as e:
                # Handle errors
                print(f"load_transaction_counter_from_log Error: Error loading transaction counter from log file: {e}")
                self.transaction_counter = 0

    def load_products_from_transaction(self, file='./data/prod_list.csv'):
        if not os.path.exists(file):
            print(f"Warning: The file '{file}' was not found.")
            return []

        try:
            df = pd.read_csv(file)
            self.product_prices = pd.Series(df['Price_per_Unit'].values,
                                            index=df['Product_Name']).to_dict()
            return df['Product_Name'].unique()
        except Exception as e:
            print(f"Error loading products from file: {e}")
            return []
    def add_product(self, product_name):
        if product_name in self.product_quantities:
            self.product_quantities[product_name] += 1
        else:
            self.product_quantities[product_name] = 1

        # Update the total price
        self.total_price += self.product_prices.get(product_name, 0)

    def remove_product(self, product_name):
        if product_name in self.product_quantities:
            self.product_quantities[product_name] -= 1
            if self.product_quantities[product_name] == 0:
                del self.product_quantities[product_name]

            self.total_price -= self.product_prices.get(product_name, 0)

    def clear_transaction(self):
        self.product_quantities.clear()
        self.total_price = 0.0

    def get_transaction_items(self):
        return self.product_quantities

    def get_total_price(self):
        return self.total_price
    
    def save_transaction(self, customer_id='Anonymous'):
        transaction_id = datetime.now().strftime('%Y%m%d%H%M%S')
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Prepare the data for saving
        transaction_data = []
        for product, quantity in self.product_quantities.items():
            transaction_data.append({
                'Transaction_ID': transaction_id,
                'Product_Name': product,
                'Quantity': quantity,
                'Transaction_Date': transaction_date,
                'Unit_Price': self.product_prices.get(product, 0),
                'Customer_ID': customer_id
            })

        # Write the transaction data to retail-data.csv
        csv_file = './data/retail-data.csv'
        try:
            with open(csv_file, 'a', newline='') as file:
                writer = csv.DictWriter(file,
                                        fieldnames=['Transaction_ID', 'Product_Name', 'Quantity', 'Transaction_Date',
                                                    'Unit_Price', 'Customer_ID'])
                if file.tell() == 0:
                    writer.writeheader()
                writer.writerows(transaction_data)
            print("Transaction saved successfully.")
        except Exception as e:
            print(f"Failed to save transaction: {e}")
