import sqlite3

# Path to the database file
db_path = './data/recommendation_system.db'

# Connect to the database
conn = sqlite3.connect(db_path)

# Function to get the list of all tables in the database
# Connect to the database
conn = sqlite3.connect(db_path)

# Function to get the list of all tables in the database
def get_tables(conn):
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    tables = conn.execute(query).fetchall()
    return [table[0] for table in tables]

# Function to get the structure of a table
def get_table_structure(conn, table_name):
    query = f"PRAGMA table_info({table_name});"
    structure = conn.execute(query).fetchall()
    return structure

# Function to get sample data from a table
def get_sample_data(conn, table_name, limit=5):
    query = f"SELECT * FROM {table_name} LIMIT {limit};"
    sample_data = conn.execute(query).fetchall()
    return sample_data

# Function to count records in a table
def count_records(conn, table_name):
    query = f"SELECT COUNT(*) FROM {table_name};"
    count = conn.execute(query).fetchone()[0]
    return count

# Example usage
tables = get_tables(conn)
print("Tables:", tables)

# For each table, print the structure, some sample data, and count of records
for table in tables:
    print(f"\nStructure of {table}:")
    print(get_table_structure(conn, table))
    
    print(f"\nSample data from {table}:")
    print(get_sample_data(conn, table))
    
    print(f"\nNumber of records in {table}:")
    print(count_records(conn, table))

# Close the connection when done
conn.close()
