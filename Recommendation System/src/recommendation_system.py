from src.recommendation import load_association_rules, get_related_recommendations, get_db_connection
from src.metric import MetricsCalculator
from src.training import data_preparation, model_training
from src.pipeline import TransactionPipeline

import smtplib
from tkinter import filedialog, messagebox, Toplevel, ttk, Entry, Text, Button
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import tkinter as tk
import sqlite3


class RecommendationSystem:
    def __init__(self):
        # Initialize recommendation system components
        self.rules_df = None
        self.pipeline = TransactionPipeline()
        self.metrics_calculator = MetricsCalculator()
        self.cached_recommendations = {}
        self.attachment_files = []
        

    def load_rules(self):
        # Load association rules
        self.rules_df = load_association_rules()
        if self.rules_df.empty:
            print("No rules were loaded.")
        # else:
        #     pass
            # print(f"Loaded {len(self.rules_df)} rules.")
            # print(self.rules_df.head())

    def update_recommendations(self, scanned_items):
        # Ensure the rules are loaded
        if self.rules_df is None or self.rules_df.empty:
            self.load_rules()

        # Get the recommendations for the scanned items
        recommendations = get_related_recommendations(scanned_items, self.rules_df)
        return recommendations


    def checkout(self, transaction_id, purchased_items, recommended_items):
        # Log the transaction and recommendations
        self.pipeline.save_log(transaction_id, recommended_items, purchased_items)
        print("Transaction logged successfully.")

    def show_shelf_recommendations(self, limit=None):
        # Return top recommendations for display in the UI
        if self.rules_df is None or self.rules_df.empty:
            self.load_rules()

        # Limit recommendations if needed
        return self.rules_df.head(limit)
    
    def fetch_data(self):
        # Clear data from the transactions and anonymization_logs tables
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Clear the existing transactions and anonymization logs
            cursor.execute('DELETE FROM transactions')
            cursor.execute('DELETE FROM sqlite_sequence WHERE name="transactions"')
            cursor.execute('DELETE FROM anonymization_logs')
            cursor.execute('DELETE FROM sqlite_sequence WHERE name="anonymization_logs"')

            conn.commit()
            print("Cleared existing transaction and log data.")
        except Exception as e:
            conn.rollback()
            print(f"Error clearing tables: {e}")
            raise e 
        finally:
            cursor.close()
            conn.close()

        # Process new data and save transactions
        self.pipeline.process_new_data()
        print("New data fetched and inserted into the transactions table.")

    def train_model(self):
        # Database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch transaction data directly from the transactions table
        cursor.execute("SELECT * FROM transactions")
        transactions = cursor.fetchall()

        if not transactions or len(transactions) == 0:
            raise ValueError("No transaction data available for model training.")

        cursor.close()
        conn.close()

        processed_transactions = data_preparation(transactions)

        model_training(processed_transactions, min_support=0.009, lift_threshold=1, confidence_threshold=0.1)
        print("Model training completed successfully.")


    def show_metrics(self):
        log_df = self.metrics_calculator.load_recommendation_logs()
        # Calculate and return metrics
        anonymized_percentage = self.metrics_calculator.calculate_anonymized_percentage()
        transparency_percentage = self.metrics_calculator.calculate_transparency_percentage()
        ranked_metrics_df = self.metrics_calculator.calculate_ranked_metrics(log_df)
        aggregated_metrics = self.metrics_calculator.calculate_aggregated_metrics(ranked_metrics_df)
        coverage_rate = self.metrics_calculator.calculate_purchase_recommendation_coverage(ranked_metrics_df)

        metrics = {
            "anonymized_percentage": anonymized_percentage,
            "transparency_percentage": transparency_percentage,
            "aggregated_metrics": aggregated_metrics,
            "coverage_rate": coverage_rate
        }
        return metrics
    
    def get_metric_warnings(self):
        return self.metrics_calculator.get_warnings()
    
    def show_metrics_graph(self):
        # Display metrics graphs
        self.metrics_calculator.show_metrics_graph()

    # Feedback-related
    def open_feedback_window(self, root):
        self.feedback_window = Toplevel(root)
        self.feedback_window.title("Send Feedback")
        self.feedback_window.geometry("400x450")

        # Feedback form label
        feedback_label = ttk.Label(self.feedback_window, text="Send Feedback to Developer", font=("Arial", 14, "bold"))
        feedback_label.pack(pady=10)

        # Developer email label and entry
        developer_email_label = ttk.Label(self.feedback_window, text="Developer Email", font=("Arial", 12))
        developer_email_label.pack(anchor="w", padx=10)
        developer_email_entry = Entry(self.feedback_window, width=40, font=("Arial", 12), state='readonly')
        developer_email_entry.pack(pady=5)
        developer_email_entry.insert(0, "developer@mail.com")

        # Sender email label and entry
        sender_email_label = ttk.Label(self.feedback_window, text="Your Email", font=("Arial", 12))
        sender_email_label.pack(anchor="w", padx=10)
        sender_email_entry = Entry(self.feedback_window, width=40, font=("Arial", 12))
        sender_email_entry.pack(pady=5)

        # Feedback message label and text box
        feedback_message_label = ttk.Label(self.feedback_window, text="Your Message", font=("Arial", 12))
        feedback_message_label.pack(anchor="w", padx=10)
        feedback_text = Text(self.feedback_window, height=8, width=40)
        feedback_text.pack(pady=10)

        # Attachment button
        attach_button = Button(self.feedback_window, text="Attach Files", font=("Arial", 12), bg="#f39c12", fg="white",
                               command=lambda: self.attach_files())
        attach_button.pack(pady=5)

        # Show names of attached files
        attachment_label = ttk.Label(self.feedback_window, text="", font=("Arial", 10), foreground="green")
        attachment_label.pack(pady=5)

        # Submit button
        submit_button = Button(self.feedback_window, text="Submit", font=("Arial", 12), bg="#27ae60", fg="white",
                               command=lambda: self.submit_feedback(sender_email_entry.get().strip(),
                                                                    feedback_text.get("1.0", "end").strip(),
                                                                    developer_email_entry.get()))
        submit_button.pack(pady=10)

    # File attachment
    def attach_files(self):
        files = filedialog.askopenfilenames(title="Select files", filetypes=(("All Files", "*.*"),))
        if files:
            self.attachment_files.extend(files)
            attached_files = ', '.join([file.split('/')[-1] for file in self.attachment_files])
            print(f"Attached: {attached_files}")

    # Submits the feedback with attachments
    def submit_feedback(self, sender_email, feedback_message, developer_email):
        if sender_email and feedback_message:
            # Create email
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = developer_email
            msg['Subject'] = "Feedback from POS System"

            # Feedback message
            msg.attach(MIMEText(feedback_message, 'plain'))

            # Attach all selected files
            for file_path in self.attachment_files:
                try:
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={file_path.split('/')[-1]}")
                        msg.attach(part)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to attach file: {str(e)}")
                    return

            # Send email
            try:
                smtp_server = smtplib.SMTP('smtp.example.com', 587)
                smtp_server.starttls()
                smtp_server.login("your_email@example.com", "your_password")
                smtp_server.sendmail(sender_email, developer_email, msg.as_string())
                smtp_server.quit()

                messagebox.showinfo("Success", "Feedback sent successfully!")
                self.feedback_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send feedback. Error: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Your email and feedback message cannot be empty.")
            
    def show_table_data(self, table_name):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Query the table based on the provided table name
            query = f"SELECT * FROM {table_name}"
            cursor.execute(query)
            rows = cursor.fetchall()

            # Fetch the column names to use them as headers
            column_names = [description[0] for description in cursor.description]

            conn.close()

            if rows:
                return {"columns": column_names, "rows": rows}
            else:
                return {"columns": column_names, "rows": []}

        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            return None
        except Exception as e:
            print(f"General error: {e}")
            return None
    
    def show_logs_popup(self, root):
        # Create a pop-up window for logs
        log_window = tk.Toplevel(root)
        log_window.title("Table Logs")
        log_window.geometry("800x600")

        # List of table names to display in the combobox
        table_names = ['recommendation_logs', 'transactions', 'association_rules', 'anonymization_logs']

        # Create a label and a combobox for table selection
        table_label = ttk.Label(log_window, text="Select Table:", font=("Arial", 12))
        table_label.pack(pady=10)

        table_combobox = ttk.Combobox(log_window, values=table_names, font=("Arial", 12))
        table_combobox.pack(pady=10)
        table_combobox.current(0)

        # Create a frame to display the table data
        table_frame = tk.Frame(log_window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Initial load of data for the first table
        self.show_selected_table(table_frame, table_combobox.get())

        # Bind the combobox selection to automatically update the table when changed
        table_combobox.bind("<<ComboboxSelected>>", lambda event: self.show_selected_table(table_frame, table_combobox.get()))

    def show_selected_table(self, table_frame, table_name):
        # Clear the previous table data
        for widget in table_frame.winfo_children():
            widget.destroy()

        # Fetch and display the selected table's data
        table_data = self.show_table_data(table_name)
        if table_data:
            self.display_table_data_in_popup(table_frame, table_data)

    def display_table_data_in_popup(self, table_frame, table_data):
        # Create a frame for the Treeview and scrollbars
        tree_frame = tk.Frame(table_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create the Treeview widget to display the table data
        tree = ttk.Treeview(tree_frame, columns=table_data["columns"], show='headings')
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Define columns in the Treeview
        for col in table_data["columns"]:
            tree.heading(col, text=col)
            tree.column(col, anchor="center")

        # Add a vertical scrollbar to the Treeview
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=v_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add a horizontal scrollbar to the Treeview
        # h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        # tree.configure(xscroll=h_scrollbar.set)
        # h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Insert the rows into the Treeview
        for row in table_data["rows"]:
            tree.insert("", "end", values=row)
            
    
    
    

# if __name__ == "__main__":
#     root = tk.Tk()
#     recommendation_system = RecommendationSystem()
#     recommendation_system.open_feedback_window(root)
#     root.mainloop()
#     recommendation_system.show_metrics()
#     recommendation_system.load_rules()
#     recommendation_system.update_recommendations(scanned_items=['tomato', 'onion', 'garlic'])
#     recommendation_system.checkout(transaction_id=1, purchased_items=['tomato', 'onion', 'garlic'], recommended_items=['tomato', 'onion', 'garlic'])
#     recommendation_system.show_shelf_recommendations()