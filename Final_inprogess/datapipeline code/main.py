import pipeline
import pandas as pd

data_pipe = pipeline.TransactionPipeline()

# Get data from POS system
data = pd.read_csv('retail-data.csv')
product_lists = data.groupby('InvoiceNo')['Description'].apply(list).tolist()

# Save product to CSV and create log
for products in product_lists:
    data_pipe.save_transaction(products)

# Initialize the TrainingPipeline class
training_pipeline = TrainingPipeline(filepath='retail-data.csv')

# Prepare data for the model
basket = training_pipeline.prepare_data()

# Train the model with prepared data and get relevant rules
relevant_rules = training_pipeline.train_model()

# Output the relevant rules
print(relevant_rules)
