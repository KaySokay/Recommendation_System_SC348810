import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from src.recommendation import get_db_connection

class MetricsCalculator:
    def __init__(self, precision_threshold=0.5, recall_threshold=0.5, anonymization_threshold=90.0,
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
            cursor.execute('SELECT transaction_id, recommended_items, purchased_items FROM recommendation_logs')
            logs = cursor.fetchall()
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
            cursor.execute('SELECT Status FROM anonymization_logs')
            logs = cursor.fetchall()
            total_records = len(logs)
            successful_anonymizations = sum(1 for log in logs if log[0] == 'Success')

            if total_records == 0:
                return 0.0
            return (successful_anonymizations / total_records) * 100
        except Exception as e:
            print(f"Error calculating anonymized percentage: {e}")
            return 0.0
        finally:
            conn.close()

    def calculate_transparency_percentage(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT confidence, lift, support FROM association_rules')
            rules = cursor.fetchall()

            total_recommendations = len(rules)
            valid_explanations = sum(1 for rule in rules if all(rule))

            if total_recommendations == 0:
                return 0.0
            return (valid_explanations / total_recommendations) * 100
        except Exception as e:
            print(f"Error calculating transparency percentage: {e}")
            return 0.0
        finally:
            conn.close()

    def calculate_ranked_metrics(self, log_df, max_k=5):
        if log_df.empty:
            print("No recommendation logs found.")
            return pd.DataFrame()

        try:
            def precision_at_k(recommended_items, purchased_items, k):
                recommended_at_k = recommended_items[:k]
                relevant_items = set(recommended_at_k).intersection(set(purchased_items))
                return len(relevant_items) / k if k > 0 else 0.0

            def recall_at_k(recommended_items, purchased_items, k):
                recommended_at_k = recommended_items[:k]
                relevant_items = set(recommended_at_k).intersection(set(purchased_items))
                return len(relevant_items) / len(purchased_items) if len(purchased_items) > 0 else 0.0

            precision_k_list = []
            recall_k_list = []

            for _, row in log_df.iterrows():
                recommended_items_str = row['recommended_items']
                purchased_items_str = row['purchased_items']
                
                if pd.isna(recommended_items_str) or pd.isna(purchased_items_str):
                    precision_k_list.append(0)
                    recall_k_list.append(0)
                    continue
                
                recommended_items = [item.strip() for item in recommended_items_str.split(',')]
                purchased_items = [item.strip() for item in purchased_items_str.split(',')]
                k = min(max_k, len(recommended_items))

                precision_k = precision_at_k(recommended_items, purchased_items, k)
                recall_k = recall_at_k(recommended_items, purchased_items, k)
                precision_k_list.append(precision_k)
                recall_k_list.append(recall_k)

            return pd.DataFrame({
                'Precision@K': precision_k_list,
                'Recall@K': recall_k_list
            })
        except Exception as e:
            print(f"Error calculating ranked metrics: {e}")
            return pd.DataFrame()

    def calculate_aggregated_metrics(self, log_df):
        try:
            if log_df.empty:
                print("Error: The log DataFrame is empty.")
                return {'Average Precision@K': 0.0, 'Average Recall@K': 0.0, 'Percentage Meeting Precision@K Threshold': 0.0}

            average_precision_k = log_df['Precision@K'].mean()
            average_recall_k = log_df['Recall@K'].mean()

            # # Debug: Check the Precision@K values
            # print("Precision@K values:")
            # print(log_df['Precision@K'])

            # Debug: Adjusting the threshold
            percentage_meeting_threshold = (log_df['Precision@K'] >= self.precision_threshold).mean() * 100
            # print(f"Percentage Meeting Precision@K Threshold: {percentage_meeting_threshold}%")

            return {
                'Average Precision@K': average_precision_k,
                'Average Recall@K': average_recall_k,
                'Percentage Meeting Precision@K Threshold': percentage_meeting_threshold
            }
        except KeyError as e:
            print(f"Error: Missing expected column in the log DataFrame - {e}")
            return {'Average Precision@K': 0.0, 'Average Recall@K': 0.0, 'Percentage Meeting Precision@K Threshold': 0.0}
        except Exception as e:
            print(f"An unexpected error occurred while calculating aggregated metrics: {e}")
            return {'Average Precision@K': 0.0, 'Average Recall@K': 0.0, 'Percentage Meeting Precision@K Threshold': 0.0}

    def calculate_purchase_recommendation_coverage(self, log_df):
        try:
            if log_df.empty:
                print("Error: The log DataFrame is empty.")
                return 0.0

            total_purchased_transactions = log_df['purchased_items'].dropna().count()
            recommended_for_purchases_transactions = log_df[~log_df['recommended_items'].isna() & 
                                                            (log_df['recommended_items'].str.strip() != '')].count()['purchased_items']

            if total_purchased_transactions == 0:
                return 0.0

            return (recommended_for_purchases_transactions / total_purchased_transactions) * 100
        except KeyError as e:
            print(f"Error: Missing expected column in the log DataFrame - {e}")
            return 0.0
        except Exception as e:
            print(f"An unexpected error occurred while calculating purchase recommendation coverage: {e}")
            return 0.0

    def get_warnings(self):
        anonymized_percentage = self.calculate_anonymized_percentage()
        transparency_percentage = self.calculate_transparency_percentage()
        log_df = self.load_recommendation_logs()

        ranked_metrics_df = self.calculate_ranked_metrics(log_df)
        aggregated_metrics = self.calculate_aggregated_metrics(ranked_metrics_df)
        coverage_rate = self.calculate_purchase_recommendation_coverage(log_df)

        warnings = []
        if aggregated_metrics.get('Average Precision@K', 0.0) < self.precision_threshold:
            warnings.append(f"Warning: Average Precision@K ({aggregated_metrics['Average Precision@K']:.2f}) fell below {self.precision_threshold}.")
        if aggregated_metrics.get('Average Recall@K', 0.0) < self.recall_threshold:
            warnings.append(f"Warning: Average Recall@K ({aggregated_metrics['Average Recall@K']:.2f}) fell below {self.recall_threshold}.")
        if anonymized_percentage < self.anonymization_threshold:
            warnings.append(f"Warning: Anonymized Percentage ({anonymized_percentage:.2f}%) fell below {self.anonymization_threshold}%.")
        if transparency_percentage < self.transparency_threshold:
            warnings.append(f"Warning: Transparency Percentage ({transparency_percentage:.2f}%) fell below {self.transparency_threshold}%.")
        if coverage_rate < self.coverage_threshold:
            warnings.append(f"Warning: Coverage Rate ({coverage_rate:.2f}%) fell below {self.coverage_threshold}%.")
        
        return warnings

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
