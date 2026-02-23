"""
Gemini API provider implementation.
"""

import time
import requests
from typing import Optional
from app.llm.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """Gemini API provider using REST API."""

    def get_provider_name(self) -> str:
        return "Gemini"

    async def generate(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generate text using Gemini API.

        Args:
            prompt: Input prompt text
            max_retries: Maximum number of retry attempts

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails after all retries
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Gemini API REST endpoint (API 키는 헤더로 전달 - URL 노출 방지)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

                headers = {
                    'Content-Type': 'application/json',
                    'x-goog-api-key': self.api_key
                }

                payload = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                }

                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()

                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

                return response_text

            except requests.exceptions.HTTPError as e:
                # Rate limit handling
                if e.response.status_code == 429:
                    wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                    last_error = f"Rate Limit exceeded (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s..."
                    print(f"[Gemini] {last_error}")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                    continue
                else:
                    last_error = f"API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    print(f"[Gemini] {last_error}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    continue

            except Exception as e:
                last_error = f"Generation failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                print(f"[Gemini] {last_error}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue

        raise Exception(f"Gemini generation failed: {last_error}")
