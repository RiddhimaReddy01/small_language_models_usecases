"""Gemini API wrapper with model selection and deprecation handling."""
import os
import time
from typing import Optional, Tuple

import google.generativeai as genai

class GeminiClient:
    """Wrapper for Gemini API with rate-limit handling."""

    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """Initialize Gemini client."""
        self.api_key = api_key
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.rate_limited = False
        self.deprecated = False
        self.error_message = None

    @staticmethod
    def _extract_text(response) -> str:
        """Safely extract text without tripping SDK convenience accessors."""
        parts = []

        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)

        return "\n".join(parts).strip()

    def generate(self, instruction: str, max_retries: int = 3) -> Tuple[str, float, int]:
        """
        Generate response with rate-limit handling.

        Returns:
            Tuple of (response_text, latency_sec, output_tokens) or (None, 0, 0) if rate limited
        """
        for attempt in range(max_retries):
            try:
                start_time = time.time()

                prompt = f"Follow the instruction exactly.\n\nInstruction:\n{instruction}\n\nResponse:"

                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                        max_output_tokens=120,
                    ),
                )

                latency = time.time() - start_time

                text = self._extract_text(response)
                if "Response:" in text:
                    text = text.split("Response:")[-1].strip()

                # Estimate token count (rough: ~4 chars per token)
                output_tokens = len(text) // 4 if text else 0
                return text, latency, output_tokens

            except Exception as e:
                error_str = str(e).lower()

                # Check for rate limiting
                if "rate" in error_str or "429" in error_str or "quota" in error_str:
                    self.rate_limited = True
                    self.deprecated = True
                    self.error_message = f"Deprecated after rate limit: {str(e)}"
                    print(f"[RATE_LIMITED] {self.model_name} hit a quota limit and will be deprecated for the rest of this run: {str(e)}")
                    return None, 0, 0

                # Check for model not found or authentication errors
                elif "not found" in error_str or "authentication" in error_str or "api key" in error_str or "permission" in error_str or "403" in error_str:
                    self.rate_limited = True
                    self.deprecated = True
                    self.error_message = f"Deprecated after model/auth error: {str(e)}"
                    print(f"[ERROR] {self.model_name} unavailable and deprecated for the rest of this run: {str(e)[:100]}")
                    return None, 0, 0

                # Retry on other errors
                elif attempt < max_retries - 1:
                    print(f"[RETRY] {attempt + 1}/{max_retries}: {str(e)[:100]}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"[ERROR] Gemini failed after {max_retries} attempts: {str(e)[:100]}")
                    return None, 0, 0

        return None, 0, 0

    def is_available(self) -> bool:
        """Check if API is available."""
        return not self.deprecated
