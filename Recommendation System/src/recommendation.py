from datetime import datetime
import pandas as pd
import sqlite3
import ast

def get_db_connection():
    try:
        # Connect to the SQLite database for the recommendation system
        conn = sqlite3.connect('./data/recommendation_system.db')  # This creates the database if it doesn't exist
        cursor = conn.cursor()

        # Create recommendation_logs table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendation_logs (
                transaction_id TEXT,
                recommended_items TEXT,
                purchased_items TEXT,
                timestamp TEXT
            )
        ''')

        # Create association_rules table if not exists
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

        # Create anonymization_logs table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anonymization_logs (
                Transaction_ID TEXT,
                Anonymization_Timestamp TEXT,
                Status TEXT
            )
        ''')

        # Create transactions table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT,
                products TEXT,
                datetime TEXT
            )
        ''')

        conn.commit()
        cursor.close()

        # print("Database and tables created or already exist.")
        return conn

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return None

    except Exception as e:
        print(f"General error: {e}")
        return None


def load_association_rules():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT antecedents, consequents, support, confidence, lift, leverage FROM association_rules')
        rules = cursor.fetchall()

        if not rules:
            print("Error: No association rules found in the database.")
            return pd.DataFrame()

        # Create a DataFrame with all metrics
        df = pd.DataFrame(rules, columns=['antecedents', 'consequents', 'support', 'confidence', 'lift', 'leverage'])
        # print("Loaded association rules:")
        # print(df.head())

        return df

    except Exception as e:
        print(f"Error loading association rules from the database: {e}")
        return pd.DataFrame()

    finally:
        conn.close()



def save_log(transaction_id, recommended_items, purchased_items):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    recommended_str = ', '.join(recommended_items) if recommended_items else 'None'
    purchased_str = ', '.join(purchased_items) if purchased_items else 'None'  # Ensure this is correct

    try:
        cursor.execute('''
            INSERT INTO recommendation_logs (transaction_id, recommended_items, purchased_items, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (transaction_id, recommended_str, purchased_str, timestamp))
        conn.commit()
        print("Log saved successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Failed to save log: {str(e)}")
    finally:
        conn.close()



# Get recommendations items
def get_related_recommendations(scanned_items, rules_df):
    if not scanned_items:
        return []

    scanned_items_set = set(item.strip().lower() for item in scanned_items)
    # print(f"Scanned items: {scanned_items_set}")

    # Antecedents set for comparison
    rules_df['antecedents_set'] = rules_df['antecedents'].apply(
        lambda x: set(item.strip().lower() for item in x.split(','))
    )

    # Filter the scanned items are in the antecedents
    relevant_rules = rules_df[
        rules_df['antecedents_set'].apply(lambda antecedent: bool(antecedent & scanned_items_set))
    ]

    if relevant_rules.empty:
        print("No relevant rules found for the scanned items.")
        return []

    # Collect all consequents associated confidence scores
    recommendations = []
    scanned_items_lower = set(item.lower() for item in scanned_items)

    for _, row in relevant_rules.iterrows():
        confidence = row['confidence']
        consequents = [item.strip() for item in row['consequents'].split(',')]
        for item in consequents:
            item_lower = item.lower()
            in_cart = item_lower in scanned_items_lower
            recommendations.append({
                'item': item,
                'confidence': confidence,
                'in_cart': in_cart
            })

    if not recommendations:
        print("No recommendations found.")
        return []

    # Create a DataFrame to handle duplicates and sorting
    recommendations_df = pd.DataFrame(recommendations)

    # Remove duplicates keeping the highest confidence
    recommendations_df = recommendations_df.sort_values('confidence', ascending=False)
    recommendations_df = recommendations_df.drop_duplicates(subset='item', keep='first')

    # Prioritize items already in the cart
    recommendations_df['priority'] = recommendations_df['in_cart'].apply(lambda x: 0 if x else 1)

    # Sort by priority items in cart and by confidence
    recommendations_df = recommendations_df.sort_values(['priority', 'confidence'], ascending=[True, False])

    # List of recommendations with "(Already in cart)" label
    final_recommendations = []
    for _, row in recommendations_df.iterrows():
        item_name = row['item']
        if row['in_cart']:
            item_name += " (Already in cart)"
        final_recommendations.append(item_name)

    # Limit to top 5 recommendations
    final_recommendations = final_recommendations[:5]

    # print(f"Recommendations based on priority and confidence: {final_recommendations}")
    return final_recommendations




# load_association_rules()