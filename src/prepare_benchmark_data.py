#!/usr/bin/env python3
"""
Prepare benchmark data files for the 8-task overnight run.
Creates rebin_results.csv with 75 examples (15 per bin) for each task.
"""

from pathlib import Path
import pandas as pd
import numpy as np

# Define tasks and their directories
TASKS = {
    "text_generation": "text_generation",
    "code_generation": "code_generation",
    "classification": "classification",
    "maths": "maths",
    "summarization": "Summarization",
    "retrieval_grounded": "Retrieval_grounded",
    "instruction_following": "instruction_following",
    "information_extraction": "Information Extraction",
}

# Sample prompts per task
SAMPLE_PROMPTS = {
    "text_generation": [
        "Explain quantum computing in simple terms",
        "What are the benefits of renewable energy?",
        "Describe the process of photosynthesis",
        "Write a short story about a robot",
        "Explain what machine learning is",
    ],
    "code_generation": [
        "Write a function to reverse a string",
        "Implement bubble sort algorithm",
        "Create a function to calculate factorial",
        "Write code to parse JSON",
        "Implement binary search",
    ],
    "classification": [
        "Classify sentiment: 'This movie was amazing!' ",
        "Classify sentiment: 'Terrible experience, never again'",
        "Classify sentiment: 'It was okay, nothing special'",
        "Categorize text: Political or Sports?",
        "Is this email spam or not spam?",
    ],
    "maths": [
        "Solve: 2x + 5 = 13",
        "Calculate: (12 + 8) * 3 - 5",
        "What is the square root of 144?",
        "Solve: 3x^2 + 2x - 1 = 0",
        "Calculate: (5! + 3!) / 4",
    ],
    "summarization": [
        "Summarize: The quick brown fox jumps over the lazy dog. The dog was sleeping peacefully.",
        "Summarize article about climate change in 2-3 sentences",
        "Summarize the key points of quantum mechanics",
        "Give a brief summary of the Industrial Revolution",
        "Summarize COVID-19 pandemic timeline",
    ],
    "retrieval_grounded": [
        "Based on context, answer: What year was X invented?",
        "Using the provided text, who is the main character?",
        "From the document, what is the capital of France?",
        "According to the passage, what happened first?",
        "From the context, what is the definition of X?",
    ],
    "instruction_following": [
        "Count to 5 starting from 1",
        "List 3 colors in alphabetical order",
        "Translate 'hello' to Spanish",
        "Write the alphabet backwards",
        "List months of the year in order",
    ],
    "information_extraction": [
        "Extract person name: 'John Smith works at Microsoft'",
        "Extract location: 'The meeting is in New York'",
        "Extract date: 'Event scheduled for March 15, 2025'",
        "Extract organization: 'Alice is CEO of TechCorp'",
        "Extract all entities: 'Bob visited Paris in 2023'",
    ],
}


def create_task_data(task_name: str, task_dir: str) -> Path:
    """Create rebin_results.csv for a task with 75 examples (15 per bin)."""

    output_dir = Path(task_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / "rebin_results.csv"

    # Get sample prompts for this task
    prompts = SAMPLE_PROMPTS.get(task_name, ["Sample prompt 1", "Sample prompt 2", "Sample prompt 3"])

    # Create 75 examples: 15 per difficulty bin (0-4)
    rows = []
    example_id = 0

    for bin_id in range(5):  # 5 difficulty bins
        for count in range(15):  # 15 examples per bin
            prompt_idx = (example_id % len(prompts))
            rows.append({
                "example_id": f"{task_name}_{example_id}",
                "sample_id": f"sample_{example_id}",
                "difficulty_bin": bin_id,
                "difficulty_score": bin_id * 2.0 + np.random.random() * 1.5,  # Score 0-8ish
                "input_text": f"{prompts[prompt_idx]} (Example {count + 1})",
                "model_size": "0.5B" if "coder" not in task_name else "0.5B",
            })
            example_id += 1

    # Create DataFrame and save
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)

    print(f"Created {output_csv}: {len(df)} examples, distribution: {df['difficulty_bin'].value_counts().sort_index().to_dict()}")
    return output_csv


def main():
    print("=" * 70)
    print("PREPARING BENCHMARK DATA")
    print("=" * 70)
    print(f"Creating 75 examples per task (15 per difficulty bin)\n")

    created_files = []
    for task_name, task_dir in TASKS.items():
        try:
            csv_path = create_task_data(task_name, task_dir)
            created_files.append(csv_path)
        except Exception as e:
            print(f"ERROR creating data for {task_name}: {e}")

    print(f"\nTotal created: {len(created_files)}/8 tasks")
    print("\nReady to run overnight benchmark:")
    print("  python run_benchmark_all_8_tasks.py")


if __name__ == "__main__":
    main()
