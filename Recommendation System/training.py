import os
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules
from src.recommendation import get_db_connection

def data_preparation(raw_transactions):
    transactions = [row[1].split(', ') for row in raw_transactions]
    return transactions

def save_relevant_rules_to_db(relevant_rules):
    """
    Saves the relevant association rules to the database in a single batch insert operation.
    """
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS association_rules (
                antecedents TEXT,
                consequents TEXT,
                support REAL,
                confidence REAL,
                lift REAL,
                leverage REAL
            )
        ''')

        # Prepare the data insert
        rules_to_insert = [
            (
                ', '.join(list(map(str, row['antecedents']))),
                ', '.join(list(map(str, row['consequents']))),
                row['support'],
                row['confidence'],
                row['lift'],
                row['leverage']
            )
            for _, row in relevant_rules.iterrows()
        ]

        # Insert all the rules
        cursor.executemany('''
            INSERT INTO association_rules (antecedents, consequents, support, confidence, lift, leverage)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', rules_to_insert)

        # Commit the transaction
        conn.commit()
        print(f"{len(rules_to_insert)} relevant association rules saved to the database.")

    except Exception as e:
        # Rollback in case of any error during the transaction
        # conn.rollback()
        print(f"Error saving relevant rules to database: {e}")

    finally:
        conn.close()

def model_training(transactions, min_support=0.001, lift_threshold=0, confidence_threshold=0):
    """
    Train the recommendation model using FP-Growth and generate association rules.
    """
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

    # Save the relevant rules
    save_relevant_rules_to_db(relevant_rules)

def initial_training(initial_data_file):
    """
    Perform initial training on a dataset and prepare the transactions for model training.
    """
    # Load the initial dataset
    df = pd.read_csv(initial_data_file)
    
    # Preprocess initial dataset
    # product_lists = df.groupby('Transaction_ID')['Product_Name'].apply(list).tolist()
    df_cleaned = df['products'].dropna()
    df_cleaned = df_cleaned.drop_duplicates()
    transactions = df_cleaned.apply(lambda x: x.split(', ')).tolist()

    # Convert to the format required by the model training function
    transactions = [list(set(str(item) for item in products)) for products in transactions] 
    
    print(f"Initial training on {len(transactions)} transactions.")
    
    # Perform model training
    model_training(transactions)
