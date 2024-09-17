import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

class TrainingPipeline:
    def __init__(self, filepath, country='United Kingdom'):
        self.filepath = filepath
        self.country = country
        self.basket = None

    def prepare_data(self):
        # Read the data
        df = pd.read_csv(self.filepath)

        # Data Preprocessing
        df.dropna(inplace=True)
        df.drop_duplicates(inplace=True)

        # Remove rows where 'InvoiceNo' starts with 'C'
        df['InvoiceNo'] = df['InvoiceNo'].astype(str)
        df = df[~df['InvoiceNo'].str.contains('C')]

        # Visualize Country Distribution (Optional)
        plt.figure(figsize=(10, 6))
        sns.histplot(df['Country'], color='red', alpha=0.8)
        plt.ylabel('Frequency')
        plt.xlabel('Country')
        plt.title('Data Distribution of Country')
        plt.show()

        # Filter the dataset for the specified country
        self.basket = df[df['Country'] == self.country].groupby(['InvoiceNo', 'CustomerID']).agg({'Description': lambda s: list(set(s))})
        
        return self.basket

    def train_model(self, min_support=0.03, lift_threshold=1.5, confidence_threshold=0.8):
        if self.basket is None:
            raise ValueError("No prepared data available. Please run prepare_data() first.")
        
        # Transaction Encoding
        te = TransactionEncoder()
        te_ary = te.fit(self.basket['Description']).transform(self.basket['Description'])
        basket_encoded = pd.DataFrame(te_ary, columns=te.columns_)

        # Apply FP-Growth to find frequent itemsets
        frequent_itemsets = fpgrowth(basket_encoded, min_support=min_support, use_colnames=True).sort_values("support", ascending=False)

        # Generate association rules using the 'lift' metric
        assoc_rulesfp = association_rules(frequent_itemsets, metric="lift", min_threshold=1).sort_values('lift', ascending=False).reset_index(drop=True)

        # Filter rules with lift > 1.5 and confidence > 0.8
        relevant_rules = assoc_rulesfp[(assoc_rulesfp['lift'] > lift_threshold) & (assoc_rulesfp['confidence'] > confidence_threshold)]

        return relevant_rules
