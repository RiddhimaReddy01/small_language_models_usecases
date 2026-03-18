import time
import os
import json
import shutil
import subprocess
import psutil
import requests
from tqdm import tqdm
from typing import Dict, Any, Optional, List
from huggingface_hub import InferenceClient

class TextGenInferenceRunner:
    def __init__(
        self,
        model_path: str = None,
        n_ctx: int = 2048,
        n_threads: int = None,
        n_batch: int = 512,
        mock: bool = False,
        model_type: str = "gguf",
        gguf_engine: str = "llama_cpp",
        cloud_request_delay_s: float = 0.0,
        cloud_max_retries: int = 0,
        cloud_backoff_base_s: float = 2.0,
        cloud_timeout_s: int = 120,
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_batch = n_batch
        self.n_threads = n_threads or 12
        self.mock = mock
        self.model_type = model_type.lower()
        self.gguf_engine = gguf_engine.lower()
        self.cloud_request_delay_s = max(0.0, cloud_request_delay_s)
        self.cloud_max_retries = max(0, cloud_max_retries)
        self.cloud_backoff_base_s = max(0.1, cloud_backoff_base_s)
        self.cloud_timeout_s = max(1, cloud_timeout_s)
        self.model = None 
        self.load_time = 0.0
        self.api_key = None

    def _cloud_post(self, url: str, **request_kwargs):
        if self.cloud_request_delay_s:
            time.sleep(self.cloud_request_delay_s)

        last_error = None
        for attempt in range(self.cloud_max_retries + 1):
            try:
                response = requests.post(url, timeout=self.cloud_timeout_s, **request_kwargs)
                response.raise_for_status()
                return response
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code not in (429, 500, 502, 503, 504) or attempt >= self.cloud_max_retries:
                    raise

                retry_after = 0.0
                if exc.response is not None:
                    retry_header = exc.response.headers.get("Retry-After")
                    if retry_header:
                        try:
                            retry_after = float(retry_header)
                        except ValueError:
                            retry_after = 0.0
                sleep_s = max(retry_after, self.cloud_backoff_base_s * (2 ** attempt))
                last_error = exc
                print(
                    f"Cloud request retry {attempt + 1}/{self.cloud_max_retries} "
                    f"after HTTP {status_code}; sleeping {sleep_s:.1f}s"
                )
                time.sleep(sleep_s)
            except requests.RequestException as exc:
                if attempt >= self.cloud_max_retries:
                    raise
                sleep_s = self.cloud_backoff_base_s * (2 ** attempt)
                last_error = exc
                print(
                    f"Cloud request retry {attempt + 1}/{self.cloud_max_retries} "
                    f"after network error; sleeping {sleep_s:.1f}s"
                )
                time.sleep(sleep_s)

        if last_error:
            raise last_error
        raise RuntimeError("Cloud request failed without a captured exception.")

    def load_model(self, api_key: Optional[str] = None):
        """Prepares the model for inference."""
        self.api_key = api_key
        start_time = time.time()
        
        if self.mock:
            self.load_time = 0.0
            return self.load_time

        if self.model_type == "gguf":
            if not self.model_path:
                raise ValueError("A GGUF model path is required for local inference.")
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            if os.path.getsize(self.model_path) == 0:
                raise ValueError(f"Model file is empty: {self.model_path}")
            print(f"Loading GGUF model from {self.model_path}...")
            if self.gguf_engine == "llama_cpp":
                try:
                    from llama_cpp import Llama
                except ImportError as exc:
                    raise ImportError(
                        "llama_cpp is not installed. Install llama-cpp-python in the active environment."
                    ) from exc
                self.model = Llama(
                    model_path=self.model_path, 
                    n_ctx=self.n_ctx, 
                    n_threads=self.n_threads, 
                    n_batch=self.n_batch, 
                    verbose=False
                )
            elif self.gguf_engine == "llama_cli":
                cli_path = shutil.which("llama-cli")
                if not cli_path:
                    raise FileNotFoundError(
                        "llama-cli was not found on PATH. Install llama.cpp CLI or use --gguf_engine llama_cpp."
                    )
                self.model = cli_path
            else:
                raise ValueError(f"Unsupported GGUF engine: {self.gguf_engine}")
            self.load_time = time.time() - start_time
        elif self.model_type == "ollama":
            # API based
            self.load_time = 0.001
        elif self.model_type == "google":
            if not self.api_key:
                print("Warning: No API key provided for Google model.")
            self.load_time = 0.001
        elif self.model_type == "huggingface":
            if not self.api_key:
                print("Warning: No API key provided for Hugging Face model.")
            self.model = InferenceClient(model=self.model_path, token=self.api_key, provider="auto", timeout=self.cloud_timeout_s)
            self.load_time = 0.001
        elif self.model_type == "openai":
            if not self.api_key:
                print("Warning: No API key provided for OpenAI model.")
            self.load_time = 0.001
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
            
        return self.load_time

    def run_inference(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> tuple:
        """Runs inference and records operational metrics. Returns (response_text, metrics_dict)."""
        if self.mock:
            time.sleep(0.5)
            return f"Mock response for: {prompt[:20]}", {"ttft": 0.1, "tps": 10, "total_time": 0.5, "peak_ram_mb": 100, "tokens_generated": 5, "ram_delta_mb": 0}

        start_time = time.time()
        ttft = 0
        response_text = ""
        tokens_generated = 0

        process = psutil.Process(os.getpid())
        ram_before = process.memory_info().rss / (1024 * 1024)

        if self.model_type == "gguf":
            if not self.model:
                raise ValueError("Model not loaded.")

            if self.gguf_engine == "llama_cpp":
                output_stream = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )

                for i, chunk in enumerate(output_stream):
                    if i == 0:
                        ttft = time.time() - start_time

                    text = chunk['choices'][0]['text']
                    response_text += text
                    tokens_generated += 1
            elif self.gguf_engine == "llama_cli":
                cmd = [
                    self.model,
                    "-m", self.model_path,
                    "-c", str(self.n_ctx),
                    "-n", str(max_tokens),
                    "--temp", str(temperature),
                    "--threads", str(self.n_threads),
                    "-p", prompt,
                    "--no-display-prompt",
                ]
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True,
                )
                response_text = completed.stdout.strip()
                tokens_generated = len(response_text.split())
                ttft = (time.time() - start_time) / 10

        elif self.model_type == "ollama":
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": self.model_path,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature}
            }
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            response_text = result.get("response", "").strip()
            tokens_generated = result.get("eval_count", len(response_text.split()))
            ttft = (time.time() - start_time) / 10 # Estimated

        elif self.model_type == "google":
            # Gemini Flash
            model_id = self.model_path if "gemini" in self.model_path else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}
            }
            resp = self._cloud_post(url, json=payload)
            result = resp.json()
            
            if "candidates" in result and result["candidates"]:
                candidate = result["candidates"][0]
                parts = candidate.get("content", {}).get("parts", [])
                if parts:
                    response_text = parts[0].get("text", "").strip()
                else:
                    # Check for safety filter
                    finish_reason = candidate.get("finishReason", "UNKNOWN")
                    response_text = f"Refusal: Finish reason {finish_reason}."
            else:
                response_text = f"Error: {json.dumps(result)}"
            
            tokens_generated = len(response_text.split()) * 1.3
            ttft = (time.time() - start_time) / 5 # Estimated

        elif self.model_type == "huggingface":
            try:
                completion = self.model.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                response_text = (completion.choices[0].message.content or "").strip()
            except Exception:
                response_text = str(self.model.text_generation(prompt, max_new_tokens=max_tokens, temperature=temperature)).strip()
            tokens_generated = len(response_text.split())
            ttft = (time.time() - start_time) / 5

        elif self.model_type == "openai":
            model_id = self.model_path or "gpt-4o-mini"
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            resp = self._cloud_post(url, headers=headers, json=payload)
            result = resp.json()
            choices = result.get("choices", [])
            if choices:
                response_text = choices[0].get("message", {}).get("content", "").strip()
            usage = result.get("usage", {})
            tokens_generated = usage.get("completion_tokens", len(response_text.split()))
            ttft = (time.time() - start_time) / 5 # Estimated

        total_time = time.time() - start_time
        ram_after = process.memory_info().rss / (1024 * 1024)
        
        metrics = {
            "ttft": ttft,
            "total_time": total_time,
            "tokens_generated": tokens_generated,
            "tps": tokens_generated / total_time if total_time > 0 else 0,
            "peak_ram_mb": ram_after if self.model_type == "gguf" else 0.0,
            "ram_delta_mb": (ram_after - ram_before) if self.model_type == "gguf" else 0.0
        }

        return response_text, metrics

    def run_batch(self, tasks, output_file="results/raw_results.json"):
        results = []
        for task in tqdm(tasks, desc="Running benchmarks"):
            prompt = task.get("prompt", "")
            output, metrics = self.run_inference(prompt)
            
            result = {
                "task_id": task.get("id"),
                "task_type": task.get("task"),
                "prompt": prompt,
                "response": output,
                "metrics": metrics
            }
            results.append(result)

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
        
        return results
