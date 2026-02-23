"""
Base abstract class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
import json


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, model: str):
        """
        Initialize the provider.

        Args:
            api_key: API key for the provider
            model: Model identifier (e.g., 'gemini-2.5-flash', 'gpt-4o')

        Raises:
            ValueError: If API key is not provided or invalid
        """
        if not api_key or api_key == "your_key_here":
            raise ValueError(f"{self.get_provider_name()} API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")

        self.api_key = api_key
        self.model = model

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (e.g., 'Gemini', 'OpenAI')."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generate text from the given prompt.

        Args:
            prompt: Input prompt text
            max_retries: Maximum number of retry attempts

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails after all retries
        """
        pass

    async def generate_json(self, prompt: str, max_retries: int = 3) -> dict:
        """
        Generate JSON output from the given prompt.

        Args:
            prompt: Input prompt text
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed JSON response

        Raises:
            Exception: If generation or JSON parsing fails
        """
        response_text = await self.generate(prompt, max_retries)

        # Remove markdown code blocks if present (```json ... ```)
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            # Remove first and last lines
            response_text = '\n'.join(lines[1:-1])

        # Parse JSON
        return json.loads(response_text)

    async def generate_with_retry(
        self,
        prompt: str,
        validator: Optional[callable] = None,
        max_retries: int = 3
    ) -> Any:
        """
        Generate output with custom validation and retry logic.

        Args:
            prompt: Input prompt text
            validator: Optional validation function that takes the response
            max_retries: Maximum number of retry attempts

        Returns:
            Validated response

        Raises:
            Exception: If generation fails validation after all retries
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await self.generate(prompt, max_retries=1)

                if validator:
                    is_valid, error_msg = validator(response)
                    if not is_valid:
                        raise ValueError(f"Validation failed: {error_msg}")

                return response

            except Exception as e:
                last_error = str(e)
                print(f"[{self.get_provider_name()}] Attempt {attempt + 1}/{max_retries} failed: {last_error}")
                if attempt < max_retries - 1:
                    continue

        raise Exception(f"{self.get_provider_name()} generation failed after {max_retries} retries: {last_error}")
