import pipeline
import pandas as pd

data_pipe = pipeline.TransactionPipeline()

# Get data from POS system
data = pd.read_csv('retail-data.csv')
#product_lists = data.groupby('InvoiceNo')['Description'].apply(list).tolist()
df.info()
df.dropna(inplace=True)
df.drop_duplicates(inplace=True)
df['InvoiceNo'] = df['InvoiceNo'].astype('str')
df = df[~df['InvoiceNo'].str.contains('C')]

# Data Visualization
df['Country'].value_counts()
plt.figure(figsize=(10, 6))
sns.histplot(df.Country, color='red', alpha=0.8)
plt.ylabel('Frequency')
plt.xlabel('Country')
plt.title('Data Distribution of Country')
plt.show()

# Basket Creation
basket = df[df['Country'] == "United Kingdom"].groupby(['InvoiceNo', 'CustomerID']).agg({'Description': lambda s: list(set(s))})

# One-Hot Encoding
te = TransactionEncoder()
te_ary = te.fit(basket['Description']).transform(basket['Description'])
basket_encoded = pd.DataFrame(te_ary, columns=te.columns_)

# Frequent Itemsets Mining
frequent_itemsets = fpgrowth(basket_encoded, min_support=0.03, use_colnames=True).sort_values("support", ascending=False)

# Association Rules Generation
assoc_rulesfp = association_rules(frequent_itemsets, metric="lift", min_threshold=1).sort_values('lift', ascending=False).reset_index(drop=True)

# Display Results
print(assoc_rulesfp)

# Save Results
frequent_itemsets.to_csv('frequent_itemsets.csv', index=False)
assoc_rulesfp.to_csv('association_rules.csv', index=False)

# Save product to CSV and create log
for products in product_lists:
    data_pipe.save_transaction(products)
