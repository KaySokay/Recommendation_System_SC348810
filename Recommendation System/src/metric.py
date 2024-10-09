import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from src.recommendation import get_db_connection  # Assuming the function is in recommendation.py

class MetricsCalculator:
    def __init__(self, precision_threshold=0.7, recall_threshold=0.5, anonymization_threshold=90.0,
                 transparency_threshold=85.0, coverage_threshold=80.0):
        self.precision_threshold = precision_threshold
        self.recall_threshold = recall_threshold
        self.anonymization_threshold = anonymization_threshold
        self.transparency_threshold = transparency_threshold
        self.coverage_threshold = coverage_threshold

    def load_recommendation_logs(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Fetch recommendation logs with purchased_items and recommended_items
            cursor.execute('SELECT transaction_id, recommended_items, purchased_items FROM recommendation_logs')
            logs = cursor.fetchall()

            # Create a DataFrame
            df = pd.DataFrame(logs, columns=['transaction_id', 'recommended_items', 'purchased_items'])
            return df
        except Exception as e:
            print(f"Error loading recommendation logs from the database: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
        
    def calculate_anonymized_percentage(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Retrieve all logs from the anonymization_logs table
            cursor.execute('SELECT Status FROM anonymization_logs')
            logs = cursor.fetchall()
            
            total_records = len(logs)
            successful_anonymizations = sum(1 for log in logs if log[0] == 'Success')

            if total_records == 0:
                return 0.0
            anonymized_percentage = (successful_anonymizations / total_records) * 100
            return anonymized_percentage
        except Exception as e:
            print(f"Error calculating anonymized percentage: {e}")
            return 0.0
        finally:
            conn.close()

    def calculate_transparency_percentage(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Retrieve association rules from the database
            cursor.execute('SELECT confidence, lift, support FROM association_rules')
            rules = cursor.fetchall()

            total_recommendations = len(rules)
            valid_explanations = sum(1 for rule in rules if all(rule))

            if total_recommendations == 0:
                return 0.0
            transparency_percentage = (valid_explanations / total_recommendations) * 100
            return transparency_percentage
        except Exception as e:
            print(f"Error calculating transparency percentage: {e}")
            return 0.0
        finally:
            conn.close()

    def calculate_ranked_metrics(self, log_df, max_k=5):
        max_k = int(max_k)
        if log_df.empty:
            print("No recommendation logs found.")
            return pd.DataFrame()
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Retrieve recommendation logs
            cursor.execute('SELECT recommended_items, purchased_items FROM recommendation_logs')
            logs = cursor.fetchall()

            if len(logs) == 0:
                print("No recommendation logs found.")
                return pd.DataFrame()

            def precision_at_k(recommended_items, purchased_items, k):
                recommended_at_k = recommended_items[:k]
                relevant_items = set(recommended_at_k).intersection(set(purchased_items))
                return len(relevant_items) / k

            def recall_at_k(recommended_items, purchased_items, k):
                recommended_at_k = recommended_items[:k]
                relevant_items = set(recommended_at_k).intersection(set(purchased_items))
                if len(purchased_items) == 0:
                    return 0.0
                return len(relevant_items) / len(purchased_items)

            precision_k_list = []
            recall_k_list = []

            for recommended_items_str, purchased_items_str in logs:
                recommended_items = [item.strip() for item in recommended_items_str.split(',')]
                purchased_items = [item.strip() for item in purchased_items_str.split(',')]
                k = min(max_k, len(recommended_items))
                precision_k = precision_at_k(recommended_items, purchased_items, k)
                recall_k = recall_at_k(recommended_items, purchased_items, k)
                precision_k_list.append(precision_k)
                recall_k_list.append(recall_k)

            df = pd.DataFrame({
                'Precision@K': precision_k_list,
                'Recall@K': recall_k_list
            })

            return df
        except Exception as e:
            print(f"Error calculating ranked metrics: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def calculate_aggregated_metrics(self, log_df):
        try:
            if log_df.empty:
                print("Error: The log DataFrame is empty.")
                return {
                    'Average Precision@K': 0.0,
                    'Average Recall@K': 0.0,
                    'Percentage Meeting Precision@K Threshold': 0.0
                }

            average_precision_k = log_df['Precision@K'].mean()
            average_recall_k = log_df['Recall@K'].mean()
            precision_threshold = 0.7
            percentage_meeting_threshold = (log_df['Precision@K'] >= precision_threshold).mean() * 100

            results = {
                'Average Precision@K': average_precision_k if pd.notnull(average_precision_k) else 0.0,
                'Average Recall@K': average_recall_k if pd.notnull(average_recall_k) else 0.0,
                'Percentage Meeting Precision@K Threshold': percentage_meeting_threshold if pd.notnull(
                    percentage_meeting_threshold) else 0.0
            }
            return results
        except KeyError as e:
            print(f"Error: Missing expected column in the log DataFrame - {e}")
            return {
                'Average Precision@K': 0.0,
                'Average Recall@K': 0.0,
                'Percentage Meeting Precision@K Threshold': 0.0
            }
        except Exception as e:
            print(f"An unexpected error occurred while calculating aggregated metrics: {e}")
            return {
                'Average Precision@K': 0.0,
                'Average Recall@K': 0.0,
                'Percentage Meeting Precision@K Threshold': 0.0
            }

    def calculate_purchase_recommendation_coverage(self, log_df):
        try:
            if log_df.empty:
                print("Error: The log DataFrame is empty.")
                return 0.0

            # Debug check 'purchased_items' column exists
            log_df = self.load_recommendation_logs()
            if 'purchased_items' not in log_df.columns:
                print(f"Error: 'purchased_items' column is missing in the DataFrame. Columns available: {log_df.columns}")
                return 0.0

            total_purchased_transactions = log_df['purchased_items'].dropna().count()

            # Debug check 'recommended_items' column exists
            if 'recommended_items' not in log_df.columns:
                print(f"Error: 'recommended_items' column is missing in the DataFrame. Columns available: {log_df.columns}")
                return 0.0

            recommended_for_purchases_transactions = log_df.dropna(subset=['recommended_items']).count()['purchased_items']

            if total_purchased_transactions == 0:
                return 0.0

            coverage_rate = (recommended_for_purchases_transactions / total_purchased_transactions) * 100
            return coverage_rate

        except KeyError as e:
            print(f"Error: Missing expected column in the log DataFrame - {e}")
            return 0.0
        except Exception as e:
            print(f"An unexpected error occurred while calculating purchase recommendation coverage: {e}")
            return 0.0

    def check_metrics_threshold(self, aggregated_metrics, anonymized_percentage, transparency_percentage, coverage_rate):
        precision_below_threshold = aggregated_metrics.get('Average Precision@K', 0.0) < self.precision_threshold
        recall_below_threshold = aggregated_metrics.get('Average Recall@K', 0.0) < self.recall_threshold
        anonymization_below_threshold = anonymized_percentage < self.anonymization_threshold
        transparency_below_threshold = transparency_percentage < self.transparency_threshold
        coverage_below_threshold = coverage_rate < self.coverage_threshold

        if (precision_below_threshold or recall_below_threshold or
            anonymization_below_threshold or transparency_below_threshold or coverage_below_threshold):
            if precision_below_threshold:
                print(f"Warning: Average Precision@K ({aggregated_metrics['Average Precision@K']}) fell below the threshold of {self.precision_threshold}.")
            if recall_below_threshold:
                print(f"Warning: Average Recall@K ({aggregated_metrics['Average Recall@K']}) fell below the threshold of {self.recall_threshold}.")
            if anonymization_below_threshold:
                print(f"Warning: Anonymized Percentage ({anonymized_percentage}%) fell below the threshold of {self.anonymization_threshold}%.")
            if transparency_below_threshold:
                print(f"Warning: Transparency Percentage ({transparency_percentage}%) fell below the threshold of {self.transparency_threshold}%.")
            if coverage_below_threshold:
                print(f"Warning: Coverage Rate ({coverage_rate}%) fell below the threshold of {self.coverage_threshold}%.")
            self.trigger_retraining_or_feedback()

    def get_warnings(self):
        warnings = []
        anonymized_percentage = self.calculate_anonymized_percentage()
        transparency_percentage = self.calculate_transparency_percentage()
        
        
        log_df = self.load_recommendation_logs()
        
        if log_df.empty:
            print("No recommendation logs found.")
            return warnings
        
        # Calculate ranked metrics
        ranked_metrics_df = self.calculate_ranked_metrics(log_df)
        
        # Calculate aggregated metrics
        aggregated_metrics = self.calculate_aggregated_metrics(ranked_metrics_df)
        
        # Calculate coverage rate
        coverage_rate = self.calculate_purchase_recommendation_coverage(log_df)
        
        # Check thresholds
        if aggregated_metrics.get('Average Precision@K', 0.0) < self.precision_threshold:
            warnings.append(
                f"Warning: Average Precision@K ({aggregated_metrics['Average Precision@K']:.2f}) "
                f"fell below the threshold of {self.precision_threshold}."
            )

        if aggregated_metrics.get('Average Recall@K', 0.0) < self.recall_threshold:
            warnings.append(
                f"Warning: Average Recall@K ({aggregated_metrics['Average Recall@K']:.2f}) "
                f"fell below the threshold of {self.recall_threshold}."
            )

        if anonymized_percentage < self.anonymization_threshold:
            warnings.append(
                f"Warning: Anonymized Percentage ({anonymized_percentage:.2f}%) "
                f"fell below the threshold of {self.anonymization_threshold}%."
            )

        if transparency_percentage < self.transparency_threshold:
            warnings.append(
                f"Warning: Transparency Percentage ({transparency_percentage:.2f}%) "
                f"fell below the threshold of {self.transparency_threshold}%."
            )

        if coverage_rate < self.coverage_threshold:
            warnings.append(
                f"Warning: Coverage Rate ({coverage_rate:.2f}%) "
                f"fell below the threshold of {self.coverage_threshold}%."
            )

        return warnings

    def trigger_retraining_or_feedback(self):
        print("Triggering model retraining or sending feedback to the developer...")

    def show_metrics_graph(self):
        try:
            log_df = self.load_recommendation_logs()
            ranked_metrics_df = self.calculate_ranked_metrics(log_df)

            if ranked_metrics_df.empty:
                print("Error: Ranked metrics DataFrame is empty.")
                return

            aggregated_metrics = self.calculate_aggregated_metrics(ranked_metrics_df)
            anonymized_percentage = self.calculate_anonymized_percentage()
            transparency_percentage = self.calculate_transparency_percentage()
            coverage_rate = self.calculate_purchase_recommendation_coverage(log_df)

            self.check_metrics_threshold(aggregated_metrics, anonymized_percentage, transparency_percentage, coverage_rate)

            fig, axs = plt.subplots(2, 2, figsize=(16, 8))

            metrics_labels = ['Anonymized Data Percentage', 'Transparency Percentage', 'Purchase Coverage Rate']
            metrics_values = [anonymized_percentage, transparency_percentage, coverage_rate]
            axs[0, 0].bar(metrics_labels, metrics_values, color=['purple', 'orange', 'cyan'])
            axs[0, 0].set_ylabel('Percentage (%)')
            axs[0, 0].set_title('General Metrics')
            axs[0, 0].grid(axis='y', linestyle='--')

            labels = ['Average Precision@K', 'Average Recall@K', 'Percentage Meeting Precision Threshold']
            values = [
                aggregated_metrics.get('Average Precision@K', 0.0),
                aggregated_metrics.get('Average Recall@K', 0.0),
                aggregated_metrics.get('Percentage Meeting Precision@K Threshold', 0.0)
            ]
            axs[0, 1].bar(labels, values, color=['b', 'g', 'r'])
            axs[0, 1].set_ylabel('Percentage / Value')
            axs[0, 1].set_title('Aggregated Metrics')
            axs[0, 1].grid(axis='y', linestyle='--')

            if 'Precision@K' in ranked_metrics_df.columns:
                axs[1, 0].plot(ranked_metrics_df.index, ranked_metrics_df['Precision@K'], marker='o', linestyle='-', color='b')
                axs[1, 0].set_xlabel('Transaction Index')
                axs[1, 0].set_ylabel('Precision@K')
                axs[1, 0].set_title('Precision@K for Each Transaction')
                axs[1, 0].grid(True)

            if 'Recall@K' in ranked_metrics_df.columns:
                axs[1, 1].plot(ranked_metrics_df.index, ranked_metrics_df['Recall@K'], marker='o', linestyle='-', color='g')
                axs[1, 1].set_xlabel('Transaction Index')
                axs[1, 1].set_ylabel('Recall@K')
                axs[1, 1].set_title('Recall@K for Each Transaction')
                axs[1, 1].grid(True)

            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"An unexpected error occurred in show_metrics_graph: {e}")
