import pipeline
import training  # Import the updated training module
import pandas as pd
import os

# Check if initial training has been done
initial_data_file = 'retail-data.csv'
training_done_flag = 'initial_training_done.txt'

if not os.path.exists(training_done_flag):
    # Perform initial training
    training.initial_training(initial_data_file)

    # Create a flag to indicate initial training is done
    with open(training_done_flag, 'w') as f:
        f.write('Initial training completed.')

# Initialize transaction pipeline
data_pipe = pipeline.TransactionPipeline()

# Get data from POS system
data = pd.read_csv('retail-data.csv')
product_lists = data.groupby('InvoiceNo')['Description'].apply(list).tolist()

# Save product to CSV and create log
for products in product_lists:
    data_pipe.save_transaction(products)

# Prepare the data from saved transactions
transactions = training.data_preparation(storage_dir='transactions')

# Train the FP-Growth model using the prepared data
training.model_training(transactions, min_support=0.03, lift_threshold=1.5, confidence_threshold=0.8, log_dir='logs')
