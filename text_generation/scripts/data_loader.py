import pandas as pd
import json
import os

class TextGenDataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def load_prompts(self, task_type):
        """
        Loads prompts for a specific task type (e.g., 'summarization', 'email').
        Expected file: data/{task_type}.json or data/{task_type}.csv
        """
        json_path = os.path.join(self.data_dir, f"{task_type}.json")
        csv_path = os.path.join(self.data_dir, f"{task_type}.csv")

        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                return json.load(f)
        elif os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return df.to_dict(orient='records')
        else:
            print(f"Warning: No data found for task '{task_type}' at {json_path} or {csv_path}")
            return []

    def save_sample_data(self):
        """Creates dummy data for initial testing."""
        sample_data = [
            {
                "id": 1,
                "task": "summarization",
                "prompt": "Summarize the following text in one sentence: The Ryzen 9 7940HS is a high-end laptop processor from AMD. It features 8 cores and 16 threads, with a boost clock of up to 5.2 GHz. It is built on the Zen 4 architecture and includes an integrated Radeon 780M GPU.",
                "constraints": {"length": "one sentence", "style": "technical"}
            },
            {
                "id": 2,
                "task": "email",
                "prompt": "Write a short professional email to a client explaining that their project will be delayed by two days due to a server migration.",
                "constraints": {"tone": "professional", "length": "short"}
            }
        ]
        
        with open(os.path.join(self.data_dir, "samples.json"), 'w') as f:
            json.dump(sample_data, f, indent=4)
        print("Sample data created in data/samples.json")

if __name__ == "__main__":
    loader = TextGenDataLoader()
    loader.save_sample_data()
