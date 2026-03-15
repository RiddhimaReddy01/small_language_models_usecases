from data_loader import load_and_sample_datasets
try:
    datasets = load_and_sample_datasets()
    for name, info in datasets.items():
        print(f"Dataset: {name}, Samples: {len(info['data'])}")
    print("Data loading SUCCESS")
except Exception as e:
    print(f"Data loading FAILED: {e}")
