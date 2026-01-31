"""AI Provider Manager - handles provider registration and fallback."""

from .base import BaseAIProvider, AnalysisResult


class AIProviderManager:
    """Manages AI providers with fallback support."""

    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {}
        self._primary: str | None = None
        self._fallback_order: list[str] = []

    def register(self, provider: BaseAIProvider, is_primary: bool = False):
        """Register an AI provider.

        Args:
            provider: The AI provider instance.
            is_primary: Whether this is the primary provider.
        """
        self._providers[provider.name] = provider
        if is_primary:
            self._primary = provider.name
        self._fallback_order.append(provider.name)

    def set_primary(self, name: str):
        """Set the primary provider by name."""
        if name in self._providers:
            self._primary = name

    def set_fallback_order(self, order: list[str]):
        """Set the fallback order for providers."""
        self._fallback_order = [n for n in order if n in self._providers]

    async def analyze(
        self, messages: list[str], context: dict
    ) -> AnalysisResult:
        """Analyze messages using primary provider with fallback.

        Tries the primary provider first, then falls back to others
        in the configured order.

        Args:
            messages: List of message texts.
            context: Additional context for analysis.

        Returns:
            AnalysisResult from the first successful provider.

        Raises:
            RuntimeError: If all providers fail.
        """
        errors = []

        # Try primary first
        if self._primary and self._primary in self._providers:
            try:
                return await self._providers[self._primary].analyze(
                    messages, context
                )
            except Exception as e:
                errors.append(f"{self._primary}: {e}")

        # Try fallbacks
        for name in self._fallback_order:
            if name == self._primary:
                continue
            try:
                return await self._providers[name].analyze(messages, context)
            except Exception as e:
                errors.append(f"{name}: {e}")

        raise RuntimeError(f"All AI providers failed: {errors}")

    @property
    def available_providers(self) -> list[str]:
        """List of registered provider names."""
        return list(self._providers.keys())
