"""
OpenAI API provider implementation.
"""

import time
from typing import Optional
from app.llm.base import BaseLLMProvider

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider using official SDK."""

    def __init__(self, api_key: str, model: str):
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Please run: pip install openai"
            )
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)

    def get_provider_name(self) -> str:
        return "OpenAI"

    async def generate(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generate text using OpenAI API.

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
                # Try with temperature=0.7 first
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                    )
                except Exception as temp_error:
                    # If temperature not supported, retry with default (1.0)
                    if "temperature" in str(temp_error) and "does not support" in str(temp_error):
                        print(f"[OpenAI] Model {self.model} doesn't support temperature=0.7, using default")
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "user", "content": prompt}
                            ],
                        )
                    else:
                        raise

                return response.choices[0].message.content.strip()

            except Exception as e:
                error_str = str(e)

                # Rate limit handling
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                    last_error = f"Rate Limit exceeded (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s..."
                    print(f"[OpenAI] {last_error}")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                    continue
                else:
                    last_error = f"Generation failed (attempt {attempt + 1}/{max_retries}): {error_str}"
                    print(f"[OpenAI] {last_error}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    continue

        raise Exception(f"OpenAI generation failed: {last_error}")

    async def generate_json(self, prompt: str, max_retries: int = 3) -> dict:
        """
        Generate JSON output using OpenAI's JSON mode.

        Args:
            prompt: Input prompt text (should request JSON output)
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed JSON response

        Raises:
            Exception: If generation or JSON parsing fails
        """
        import json
        import traceback
        last_error = None

        for attempt in range(max_retries):
            try:
                # Try with temperature=0.7 first
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                    )
                except Exception as temp_error:
                    # If temperature not supported, retry with default (1.0)
                    if "temperature" in str(temp_error) and "does not support" in str(temp_error):
                        print(f"[OpenAI] Model {self.model} doesn't support temperature=0.7, using default")
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "user", "content": prompt}
                            ],
                            response_format={"type": "json_object"},
                        )
                    else:
                        raise

                response_text = response.choices[0].message.content.strip()

                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    lines = response_text.split('\n')
                    response_text = '\n'.join(lines[1:-1])

                return json.loads(response_text)

            except Exception as e:
                error_str = str(e)
                # Print full traceback for debugging
                print(f"[OpenAI] Full error traceback:")
                traceback.print_exc()

                # Rate limit handling
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    wait_time = (2 ** attempt) * 2
                    last_error = f"Rate Limit exceeded (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s..."
                    print(f"[OpenAI] {last_error}")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                    continue
                else:
                    last_error = f"JSON generation failed (attempt {attempt + 1}/{max_retries}): {error_str}"
                    print(f"[OpenAI] {last_error}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    continue

        raise Exception(f"OpenAI JSON generation failed: {last_error}")
