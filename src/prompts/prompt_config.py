"""AI model parameters and configuration.

This module defines the parameters used for AI API calls to ensure
factual, coherent, and objective output.
"""

from typing import Dict, Any


# Base AI parameters for factual analysis
AI_PARAMETERS = {
    "temperature": 0.2,
    "top_p": 0.9,
    "max_tokens": 4000,
}


def get_ai_parameters(
    preset: str = "factual",
    custom_overrides: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Get AI model parameters by preset.

    Args:
        preset: Parameter preset to use.
        custom_overrides: Optional dict to override specific parameters.

    Returns:
        Dict with temperature, top_p, max_tokens.

    Available presets:
        - factual (default): Low temp (0.2) for accurate reporting
        - balanced: Medium temp (0.5) for some creativity
        - creative: Higher temp (0.7) for diverse responses
        - concise: Shorter max_tokens (2000)
    """
    presets = {
        "factual": {
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 4000,
        },
        "balanced": {
            "temperature": 0.5,
            "top_p": 0.95,
            "max_tokens": 4000,
        },
        "creative": {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 4000,
        },
        "concise": {
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 2000,
        },
    }

    if preset not in presets:
        raise ValueError(
            f"Unknown preset: {preset}. "
            f"Available: {list(presets.keys())}"
        )

    params = presets[preset].copy()

    # Apply custom overrides if provided
    if custom_overrides:
        params.update(custom_overrides)

    return params


# Parameter explanations for documentation
PARAMETER_DOCS = {
    "temperature": {
        "range": "0.0 - 1.0",
        "description": "Controls randomness in output generation",
        "low": "More deterministic, factual (0.0-0.3)",
        "medium": "Balanced creativity and accuracy (0.4-0.6)",
        "high": "More creative, diverse (0.7-1.0)",
        "recommendation": "0.2 for factual news analysis",
    },
    "top_p": {
        "range": "0.0 - 1.0",
        "description": "Nucleus sampling - limits token selection to top cumulative probability",
        "low": "Very focused, limited vocabulary (0.5-0.7)",
        "medium": "Balanced coherence and diversity (0.8-0.9)",
        "high": "All words possible, more random (0.95-1.0)",
        "recommendation": "0.9 for coherent but not rigid analysis",
    },
    "max_tokens": {
        "range": "1 - 32000 (model dependent)",
        "description": "Maximum response length in tokens",
        "estimation": "~1 token ≈ 0.75 English words or 1 Vietnamese word",
        "examples": {
            "brief": "1000-1500 tokens",
            "standard": "2000-3000 tokens",
            "comprehensive": "4000-6000 tokens",
        },
        "recommendation": "4000 for detailed digest with multiple sections",
    },
}


def get_parameter_docs(param_name: str = None) -> Dict:
    """Get documentation for AI parameters.

    Args:
        param_name: Specific parameter to get docs for. If None, returns all.

    Returns:
        Dict with parameter documentation.
    """
    if param_name:
        if param_name not in PARAMETER_DOCS:
            raise ValueError(f"Unknown parameter: {param_name}")
        return PARAMETER_DOCS[param_name]

    return PARAMETER_DOCS


# API-specific configurations
API_CONFIGS = {
    "perplexity": {
        "model": "sonar-pro",
        "timeout": 120.0,
        "max_retries": 3,
        "retry_delay": 1,
    },
    "gemini": {
        "model": "gemini-pro",
        "timeout": 60.0,
        "max_retries": 3,
        "retry_delay": 1,
    },
    "openai": {
        "model": "gpt-4-turbo-preview",
        "timeout": 60.0,
        "max_retries": 3,
        "retry_delay": 1,
    },
}


def get_api_config(provider: str) -> Dict[str, Any]:
    """Get API-specific configuration.

    Args:
        provider: AI provider name (perplexity, gemini, openai).

    Returns:
        Dict with provider-specific settings.

    Raises:
        ValueError: If provider is not recognized.
    """
    if provider not in API_CONFIGS:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Available: {list(API_CONFIGS.keys())}"
        )

    return API_CONFIGS[provider].copy()
