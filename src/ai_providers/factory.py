"""Builds the AI provider manager from configuration."""

from ..config import config
from .deepseek import DeepSeekProvider
from .manager import AIProviderManager
from .perplexity import PerplexityProvider


def build_ai_manager() -> AIProviderManager:
    """Register every provider that has an API key.

    PRIMARY_AI_PROVIDER picks the primary. Other providers act as fallbacks.

    Raises:
        RuntimeError: If no provider has an API key.
    """
    providers = []
    if config.ai.deepseek_api_key:
        providers.append(DeepSeekProvider(config.ai.deepseek_api_key))
    if config.ai.perplexity_api_key:
        providers.append(PerplexityProvider(config.ai.perplexity_api_key))

    if not providers:
        raise RuntimeError("No AI provider configured. Set DEEPSEEK_API_KEY in .env.")

    manager = AIProviderManager()
    for provider in providers:
        manager.register(
            provider, is_primary=provider.name == config.ai.primary_provider
        )
    return manager
