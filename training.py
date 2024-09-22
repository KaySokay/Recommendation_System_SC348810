import os
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

def data_preparation(storage_dir='transactions'):
    # Initialize list to hold all transactions
    all_transactions = []
    
    # Read all CSV files with the format transaction_YYYY_MM_DD.csv
    for file in os.listdir(storage_dir):
        if file.startswith('transaction_') and file.endswith('.csv'):
            filepath = os.path.join(storage_dir, file)
            df = pd.read_csv(filepath)
            # Convert the products column back to a list of items
            transactions = df['products'].apply(lambda x: x.split(', ')).tolist()
            all_transactions.extend(transactions)
    
    # Return list of transactions for further processing
    return all_transactions

def model_training(transactions, min_support=0.03, lift_threshold=1.5, confidence_threshold=0.8, log_dir='logs'):
    # Convert transaction data into one-hot encoding
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    basket_encoded = pd.DataFrame(te_ary, columns=te.columns_)
    
    # Apply FP-Growth algorithm to find frequent itemsets
    frequent_itemsets = fpgrowth(basket_encoded, min_support=min_support, use_colnames=True).sort_values("support", ascending=False)
    
    # Generate association rules
    assoc_rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1).sort_values('lift', ascending=False).reset_index(drop=True)
    
    # Filter based on lift and confidence
    relevant_rules = assoc_rules[(assoc_rules['lift'] > lift_threshold) & (assoc_rules['confidence'] > confidence_threshold)]
    
    # Save relevant association rules
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    relevant_rules.to_csv(os.path.join(log_dir, 'relevant_rules.csv'), index=False)
    
    print(f"Model training complete. Relevant association rules saved to {os.path.join(log_dir, 'relevant_rules.csv')}")

def initial_training(initial_data_file):
    # Load the initial dataset
    df = pd.read_csv(initial_data_file)
    
    # Preprocess initial dataset
    product_lists = df.groupby('InvoiceNo')['Description'].apply(list).tolist()

    # Convert to the format required by the model training function
    transactions = [list(set(products)) for products in product_lists]  # Remove duplicates
    
    print(f"Initial training on {len(transactions)} transactions.")
    
    # Perform model training
    model_training(transactions)
