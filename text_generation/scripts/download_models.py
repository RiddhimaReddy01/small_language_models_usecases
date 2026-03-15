import os
import requests
from tqdm import tqdm

MODELS = {
    "qwen2.5-3b-instruct": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
    "phi-3.5-mini-instruct": "https://huggingface.co/Bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf"
}

def download_file(url, target_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1MB

    print(f"Downloading {os.path.basename(target_path)}...")
    with open(target_path, 'wb') as f, tqdm(
        total=total_size, unit='iB', unit_scale=True, desc=os.path.basename(target_path)
    ) as pbar:
        for data in response.iter_content(block_size):
            pbar.update(len(data))
            f.write(data)

def main():
    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)

    for name, url in MODELS.items():
        filename = os.path.basename(url)
        target_path = os.path.join(models_dir, filename)
        
        if os.path.exists(target_path):
            print(f"Model {filename} already exists at {target_path}")
            continue
            
        try:
            download_file(url, target_path)
        except Exception as e:
            print(f"Failed to download {name}: {e}")

if __name__ == "__main__":
    main()
