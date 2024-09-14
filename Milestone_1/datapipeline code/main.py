import pipeline
import pandas as pd

data_pipe = pipeline.TransactionPipeline()

# Get data from POS system
data = pd.read_csv('retail-data.csv')
product_lists = data.groupby('InvoiceNo')['Description'].apply(list).tolist()

# Save product to CSV and create log
for products in product_lists:
    data_pipe.save_transaction(products)
