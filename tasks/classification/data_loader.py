from classification_eval.datasets import get_diverse_stratified_sample, infer_text_column
from classification_eval.datasets import load_builtin_datasets as load_and_sample_datasets


if __name__ == "__main__":
    datasets = load_and_sample_datasets()
    for name, info in datasets.items():
        print(f"Dataset: {name}, Samples: {len(info['data'])}")
