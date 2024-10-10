import tkinter as tk
from tkinter import ttk
from src.pos_operations import POSOperations
from src.recommendation_system import RecommendationSystem
import threading
import time
from src.pipeline import TransactionPipeline
from tkinter import messagebox


class POSUI:
    def __init__(self, root):
        self.root = root
        self.root.title("POS System with Related Recommendations")
        self.root.geometry("1024x768")
        self.root.configure(bg="#f0f0f0")

        # POS operations and recommendations
        self.pos_operations = POSOperations()
        self.recommendation_system = RecommendationSystem() 
        self.recommendation_system.load_rules() 
        self.pipeline = TransactionPipeline()

        # UI components
        self.create_sidebar()
        self.create_main_frame()
        self.show_home()

    def create_sidebar(self):
        # Sidebar for navigation
        sidebar = tk.Frame(self.root, bg='#2c3e50', width=70)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        buttons = [("Home", self.show_home), ("Shelf Recommend", self.show_shelf_recommendations), ("Metrics", self.show_metrics)]

        for btn_text, command in buttons:
            btn = tk.Button(sidebar, text=btn_text, font=("Arial", 12), bg="#34495e", fg="white", bd=0, command=command)
            btn.pack(fill=tk.X, pady=2)

    def create_main_frame(self):
        self.content_frame = tk.Frame(self.root)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def show_home(self):
        # Clear contents
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Frame
        main_frame = tk.Frame(self.content_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Transaction Frame
        transaction_frame = tk.Frame(main_frame)
        transaction_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Transaction label
        transaction_title = ttk.Label(transaction_frame, text="Transaction List", font=("Arial", 14, "bold"))
        transaction_title.pack(anchor="w", pady=5)

        # Transaction list and product
        self.transaction_listbox = ttk.Treeview(transaction_frame, columns=("Product", "Quantity"), show="headings")
        self.transaction_listbox.heading("Product", text="Product")
        self.transaction_listbox.heading("Quantity", text="Quantity")
        self.transaction_listbox.pack(fill=tk.BOTH, expand=True)

        # Bind double-click to remove a product
        self.transaction_listbox.bind('<Double-1>', self.remove_product)

        self.update_transaction_listbox()

        # Product Frame
        product_frame = tk.Frame(main_frame)
        product_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Product list label
        product_title = ttk.Label(product_frame, text="Product List", font=("Arial", 14, "bold"))
        product_title.pack(anchor="w", pady=5)

        # Product listbox
        product_listbox = tk.Listbox(product_frame, font=("Arial", 12))
        for product in self.pos_operations.load_products_from_transaction():
            product_listbox.insert(tk.END, product)
        product_listbox.pack(fill=tk.BOTH, expand=True)
        product_listbox.bind('<Double-1>', self.add_product)

        # Recommendation Frame
        recommendation_frame = tk.Frame(self.content_frame)
        recommendation_frame.pack(fill=tk.X, padx=10, pady=10)

        # Recommendation label
        recommendation_title = ttk.Label(recommendation_frame, text="Related Recommendations",
                                         font=("Arial", 14, "bold"))
        recommendation_title.pack(anchor="w", pady=5)

        # Recommendation listbox
        self.recommendations_listbox = tk.Listbox(recommendation_frame, height=5, font=("Arial", 12))
        self.recommendations_listbox.pack(fill=tk.X, padx=10, pady=10)

        # Total price label
        self.total_price_label = ttk.Label(self.content_frame,
                                           text=f"Total: ฿{self.pos_operations.get_total_price():.2f}",
                                           font=("Arial", 20, "bold"))
        self.total_price_label.pack(anchor="w", pady=10)

        # Button frame to checkout and clear transaction buttons
        button_frame = tk.Frame(self.content_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Checkout button
        checkout_button = tk.Button(button_frame, text="Check out", font=("Arial", 12), bg="#3498db", fg="white",
                                    command=self.checkout)
        checkout_button.pack(side=tk.LEFT, padx=5)

        # Clear transaction button
        clear_transaction_button = tk.Button(button_frame, text="Clear Transaction", font=("Arial", 12), bg="#e74c3c",
                                             fg="white",
                                             command=self.clear_transaction)
        clear_transaction_button.pack(side=tk.LEFT, padx=5)

    def add_product(self, event):
        selected_product = event.widget.get(event.widget.curselection())
        self.pos_operations.add_product(selected_product)
        self.update_transaction_listbox()
        self.update_recommendations()
        self.update_total_price()

    def remove_product(self, event):
        # Get the currently selected item
        selected_item = self.transaction_listbox.focus()

        if selected_item:
            # Get product name from the selected row
            product_name = self.transaction_listbox.item(selected_item, 'values')[0]

            # Remove the product using the POSOperations method
            self.pos_operations.remove_product(product_name)

            # Update the UI elements
            self.update_transaction_listbox()
            self.update_recommendations()
            self.update_total_price()

    def update_transaction_listbox(self):
        # Clear the current contents
        self.transaction_listbox.delete(*self.transaction_listbox.get_children())

        # Add the items to the listbox
        for product, quantity in self.pos_operations.get_transaction_items().items():
            self.transaction_listbox.insert("", "end", values=(product, quantity))

    def update_recommendations(self):
        # Get the scanned items
        scanned_items = list(self.pos_operations.get_transaction_items().keys())

        # Get updated recommendations
        recommendations = self.recommendation_system.update_recommendations(scanned_items)

        # Update the UI with the recommendations
        self.recommendations_listbox.delete(0, tk.END)
        if recommendations:
            self.recommendations_listbox.insert(tk.END, "Related items you might like:")
            for rec in recommendations:
                self.recommendations_listbox.insert(tk.END, rec)


    def update_total_price(self):
        total_price = self.pos_operations.get_total_price()
        self.total_price_label.config(text=f"Total: ฿{total_price:.2f}")

    def checkout(self):
        # Get scanned items
        purchased_items = list(self.pos_operations.get_transaction_items().keys())

        # Get recommendations
        raw_recommended_items = list(self.recommendations_listbox.get(1, tk.END))
        recommended_items = [item.replace(" (Already in cart)", "") for item in raw_recommended_items]

        # Generate transaction ID
        transaction_id = self.pos_operations.generate_transaction_id()

        # Save the log of the transaction
        self.recommendation_system.checkout(transaction_id, purchased_items, recommended_items)

        # Save the current transaction data
        self.pos_operations.save_transaction(customer_id="12345")

        # Clear the transaction
        self.pos_operations.clear_transaction()
        self.update_transaction_listbox()
        self.recommendations_listbox.delete(0, tk.END)
        self.update_total_price()

    def show_shelf_recommendations(self):
        # Clear previous contents
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Shelf Recommendations label
        shelf_label = ttk.Label(self.content_frame, text="Shelf Recommendations", font=("Arial", 14, "bold"),
                                background="white")
        shelf_label.pack(anchor="w", pady=5)

        # Train Model Button
        train_model_button = tk.Button(self.content_frame, text="Train Model", font=("Arial", 12), bg="#27ae60",
                                    fg="white",
                                    command=self.open_training_window)
        train_model_button.pack(anchor="w", pady=5)

        # Frame to contain the Treeview and Scrollbar
        treeview_frame = tk.Frame(self.content_frame)
        treeview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        treeview_scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical")
        treeview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Displaying all recommendations
        columns = ("Antecedents", "Consequents", "Support", "Confidence", "Lift", "Leverage")
        self.shelf_recommendations_treeview = ttk.Treeview(treeview_frame, columns=columns, show="headings",
                                                        yscrollcommand=treeview_scrollbar.set)
        treeview_scrollbar.config(command=self.shelf_recommendations_treeview.yview)

        # Define column headings and sizes
        for col in columns:
            self.shelf_recommendations_treeview.heading(col, text=col)
            self.shelf_recommendations_treeview.column(col, anchor="center", width=150)

        self.shelf_recommendations_treeview.pack(fill=tk.BOTH, expand=True)

        # Frame dropdown selection
        dropdown_frame = tk.Frame(self.content_frame, background="white")
        dropdown_frame.pack(fill=tk.X, padx=10, pady=10)

        # Dropdown label
        dropdown_label = ttk.Label(dropdown_frame, text="Show Top Results:", font=("Arial", 12), background="white")
        dropdown_label.pack(side=tk.LEFT, padx=5)

        # Combobox for selecting number of results to display
        self.results_combobox = ttk.Combobox(dropdown_frame, values=["20", "50", "100", "200", "All"],
                                            font=("Arial", 12))
        self.results_combobox.current(0)  #set default value
        self.results_combobox.pack(side=tk.LEFT, padx=5)

        # Bind combobox
        self.results_combobox.bind("<<ComboboxSelected>>", lambda event: self.update_shelf_recommendations())

        # Display initial data
        self.update_shelf_recommendations()

        # Explanation Section
        explanation_frame = tk.Frame(self.content_frame, background="white")
        explanation_frame.pack(fill=tk.X, padx=10, pady=10)

        explanation_title = ttk.Label(explanation_frame, text="Metric Explanations", font=("Arial", 14, "bold"),
                                    background="white")
        explanation_title.pack(anchor="w", pady=5)

        explanation_text = (
            "Support: Represents the proportion of transactions that contain both the antecedent and the consequent.\n"
            "Confidence: Indicates the likelihood of the consequent being purchased if the antecedent is purchased.\n"
            "Lift: Measures how much more likely the consequent is bought when the antecedent is bought, compared to its usual frequency.\n"
            "Leverage: Represents the difference between the observed co-occurrence of antecedent and consequent and the expected co-occurrence if they were independent."
        )
        explanation_label = ttk.Label(explanation_frame, text=explanation_text, font=("Arial", 12), background="white",
                                    justify="left")
        explanation_label.pack(anchor="w")

    def update_shelf_recommendations(self):
        # Get the selected number
        selected_value = self.results_combobox.get()

        if selected_value == "All":
            limit = None
        else:
            limit = int(selected_value)

        # Clear current contents
        for item in self.shelf_recommendations_treeview.get_children():
            self.shelf_recommendations_treeview.delete(item)

        # Populate the specified number of association rules
        recommendations = self.recommendation_system.show_shelf_recommendations(limit)
        for _, row in recommendations.iterrows():
            # antecedents = ', '.join(list(row['antecedents']))
            # consequents = ', '.join(list(row['consequents']))
            antecedents = row['antecedents']
            consequents = row['consequents']
            support = round(row['support'], 4)
            confidence = round(row['confidence'], 4)
            lift = round(row['lift'], 4)
            leverage = round(row['leverage'], 4)
            self.shelf_recommendations_treeview.insert("", "end", values=(
                antecedents, consequents, support, confidence, lift, leverage))

    def open_training_window(self):
        # Create popup window
        self.training_window = tk.Toplevel(self.root)
        self.training_window.title("Model Training")
        self.training_window.geometry("300x150")

        # Progress Bar
        progress_label = ttk.Label(self.training_window, text="Training Model...", font=("Arial", 12))
        progress_label.pack(pady=10)

        # Progress Bar initialization
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.training_window, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=20, pady=10)

        # Start model training
        threading.Thread(target=self.run_model_training).start()

    def run_model_training(self):
        # Simulate progress updates
        self.progress_var.set(0)
        self.progress_bar.start()

        try:
            for i in range(10):
                time.sleep(1)
                self.progress_var.set((i + 1) * 10)
            self.recommendation_system.train_model()
        except Exception as e:
            print(f"Error during model training: {e}")
        finally:
            self.progress_bar.stop()
            self.progress_var.set(100)
            self.show_completion_message()

    def show_completion_message(self):
        completion_label = ttk.Label(self.training_window, text="Model training complete!", font=("Arial", 12),
                                     foreground="green")
        completion_label.pack(pady=10)
        self.recommendation_system.load_rules() 
        self.training_window.after(2000, self.training_window.destroy)
        self.show_shelf_recommendations()

    def clear_transaction(self):
        # Clear the current
        self.pos_operations.clear_transaction()
        self.update_transaction_listbox()
        self.recommendations_listbox.delete(0, tk.END)
        self.update_total_price()

    def show_metrics(self):
        # Clear contents
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Metrics Monitoring
        metrics_frame = tk.Frame(self.content_frame)
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        metrics_title = ttk.Label(metrics_frame, text="Metrics Monitor", font=("Arial", 14, "bold"))
        metrics_title.pack(anchor="w", pady=5)

        metrics = self.recommendation_system.show_metrics()

        metrics_text = (
            f"Anonymized Data Percentage: {metrics['anonymized_percentage']:.2f}%\n"
            f"Transparency Percentage: {metrics['transparency_percentage']:.2f}%\n"
            f"Average Precision@K: {metrics['aggregated_metrics']['Average Precision@K']:.2f}\n"
            f"Average Recall@K: {metrics['aggregated_metrics']['Average Recall@K']:.2f}\n"
            f"Percentage Meeting Precision@K Threshold: {metrics['aggregated_metrics']['Percentage Meeting Precision@K Threshold']:.2f}%\n"
            f"Purchase Recommendation Coverage: {metrics['coverage_rate']:.2f}%"
        )
        metrics_label = ttk.Label(metrics_frame, text=metrics_text, font=("Arial", 12), justify="left")
        metrics_label.pack(anchor="w", pady=5)

        # Show Graph button
        show_graph_button = tk.Button(metrics_frame, text="Show Metrics Graphs", font=("Arial", 12), bg="#3498db", fg="white",
                                    command=self.recommendation_system.show_metrics_graph)
        show_graph_button.pack(pady=10)

        # Metric Warnings Section
        warnings = self.recommendation_system.get_metric_warnings()
        if warnings:
            warning_title = ttk.Label(metrics_frame, text="Metric Warnings", font=("Arial", 14, "bold"), foreground="red")
            warning_title.pack(anchor="w", pady=5)

            for warning in warnings:
                warning_label = ttk.Label(metrics_frame, text=warning, font=("Arial", 12), foreground="red")
                warning_label.pack(anchor="w", padx=10)

            # Feedback button
            feedback_button = tk.Button(metrics_frame, text="Send Feedback", font=("Arial", 12), bg="#e67e22", fg="white",
                                        command=self.open_feedback_window)
            feedback_button.pack(pady=10)


    def open_feedback_window(self):
        self.recommendation_system.open_feedback_window(self.root)


# if __name__ == "__main__":
#     root = tk.Tk()
#     pos_ui = POSUI(root)
#     root.mainloop()
