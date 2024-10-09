import os
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

def data_preparation(storage_dir='transactions'):
    all_transactions = []
    
    for file in os.listdir(storage_dir):
        if file.startswith('transaction_') and file.endswith('.csv'):
            filepath = os.path.join(storage_dir, file)
            df = pd.read_csv(filepath)
            # Handle missing values by dropping rows with NaNs in 'products' column
            df_cleaned = df['products'].dropna()
            # Drop duplicate rows (if there are identical transactions)
            df_cleaned = df_cleaned.drop_duplicates()
            # Process transactions
            transactions = df_cleaned.apply(lambda x: x.split(', ')).tolist()
            # Convert all items in transactions to strings
            transactions = [[str(item) for item in transaction] for transaction in transactions]
            all_transactions.extend(transactions)
    
    return all_transactions


def model_training(transactions, min_support=0.035, lift_threshold=1.5, confidence_threshold=0.8, log_dir='logs'):
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
    transactions = [list(set(str(item) for item in products)) for products in product_lists] 
    
    print(f"Initial training on {len(transactions)} transactions.")
    
    # Perform model training
    model_training(transactions)
