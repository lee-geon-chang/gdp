"""
Factory for creating LLM providers based on model name.
"""

import os
from typing import Dict
from dotenv import load_dotenv
from app.llm.base import BaseLLMProvider
from app.llm.gemini import GeminiProvider
from app.llm.openai import OpenAIProvider

# Load environment variables
load_dotenv()


def parse_supported_models() -> Dict[str, dict]:
    """
    Parse supported models from environment variable.

    Returns:
        Dict mapping model ID to {"provider": str, "display": str}

    Example:
        SUPPORTED_MODELS="gemini-2.5-flash|Gemini 2.5 Flash,gpt-4o|GPT-4o"
        Returns: {
            "gemini-2.5-flash": {"provider": "gemini", "display": "Gemini 2.5 Flash"},
            "gpt-4o": {"provider": "openai", "display": "GPT-4o"}
        }
    """
    models_str = os.getenv("SUPPORTED_MODELS", "")
    models = {}

    for item in models_str.split(','):
        item = item.strip()
        if not item:
            continue

        if '|' in item:
            key, display = item.split('|', 1)
            key = key.strip()
            display = display.strip()
        else:
            key = item
            display = item

        # Auto-detect provider from model name
        if key.startswith('gemini-'):
            provider = 'gemini'
        elif key.startswith('gpt-'):
            provider = 'openai'
        else:
            provider = 'unknown'

        models[key] = {
            "provider": provider,
            "display": display
        }

    return models


# Parse supported models on module load
SUPPORTED_MODELS = parse_supported_models()


def get_supported_models() -> Dict[str, dict]:
    """
    Get the list of supported models.

    Returns:
        Dict mapping model ID to {"provider": str, "display": str}
    """
    return SUPPORTED_MODELS


def get_provider(model: str) -> BaseLLMProvider:
    """
    Factory function to create the appropriate LLM provider.

    Args:
        model: Model identifier (e.g., 'gemini-2.5-flash', 'gpt-4o')

    Returns:
        BaseLLMProvider instance

    Raises:
        ValueError: If model is not supported or API key is missing
    """
    # Get default model if not specified
    if not model:
        model = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

    # Check if model is supported
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {model}. "
            f"Supported models: {', '.join(SUPPORTED_MODELS.keys())}"
        )

    provider_name = SUPPORTED_MODELS[model]["provider"]

    # Create provider based on type
    if provider_name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
        return GeminiProvider(api_key=api_key, model=model)

    elif provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API 키가 설정되지 않았습니다. "
                ".env 파일에 OPENAI_API_KEY를 추가하세요."
            )
        return OpenAIProvider(api_key=api_key, model=model)

    else:
        raise ValueError(f"Unknown provider: {provider_name}")
