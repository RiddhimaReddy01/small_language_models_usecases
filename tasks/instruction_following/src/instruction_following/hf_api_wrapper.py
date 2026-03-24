"""Hugging Face hosted inference wrapper for instruction following."""

from __future__ import annotations

import os
import time
from typing import Optional, Tuple

from huggingface_hub import InferenceClient


class HuggingFaceClient:
    """Simple hosted text-generation client for SLM reruns."""

    def __init__(self, model_name: str, token: Optional[str] = None):
        self.model_name = model_name
        self.token = token or os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not self.token:
            raise ValueError("Hugging Face API token not found in HF_API_KEY, HF_TOKEN, or HUGGINGFACEHUB_API_TOKEN.")
        self.client = InferenceClient(model=model_name, token=self.token, provider="auto", timeout=180)

    def generate(self, instruction: str, *, max_new_tokens: int = 120, temperature: float = 0.0, top_p: float = 1.0) -> Tuple[str, float, int]:
        prompt = f"Follow the instruction exactly.\n\nInstruction:\n{instruction}\n\nResponse:"
        start = time.time()
        try:
            output = self.client.text_generation(
                prompt,
                model=self.model_name,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
                return_full_text=False,
            )
            text = str(output).strip()
        except Exception as text_exc:
            try:
                response = self.client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                text = self._extract_chat_text(response)
            except Exception as chat_exc:
                raise RuntimeError(str(chat_exc) or str(text_exc)) from chat_exc
        latency = time.time() - start
        if "Response:" in text:
            text = text.split("Response:")[-1].strip()
        output_tokens = max(1, len(text.split()))
        return text, latency, output_tokens

    def _extract_chat_text(self, response) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""
        content = getattr(message, "content", "")
        if isinstance(content, list):
            parts = []
            for item in content:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
            return "\n".join(parts).strip()
        return str(content or "").strip()
