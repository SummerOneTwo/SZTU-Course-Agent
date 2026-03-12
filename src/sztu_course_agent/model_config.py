"""Model configuration module for LLM provider selection.

This module handles model configuration and selection using LiteLLM format.
Supports multiple LLM providers including OpenAI, Anthropic, Google, DeepSeek, and local models.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelInfo:
    """Information about the selected model configuration."""
    provider: str
    model: str
    display_name: str
    api_key_env: str


# Default models for each provider
DEFAULT_MODELS = {
    "openai": "openai/gpt-4o-mini",
    "claude": "anthropic/claude-3-5-sonnet-20241022",
    "gemini": "gemini/gemini-2.0-flash-exp",
    "deepseek": "deepseek/deepseek-chat",
    "local": "ollama/llama3.2",
}

# API key environment variables for each provider
API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "local": None,  # Local models don't require API key
}

# Base URLs for providers that need them
BASE_URLS = {
    "local": "http://localhost:11434",  # Default Ollama URL
}


def get_provider() -> str:
    """Get the LLM provider from environment variable.

    Returns:
        The provider name (default: "openai")
    """
    return os.getenv("LLM_PROVIDER", "openai").lower()


def get_model(provider: Optional[str] = None) -> str:
    """Get the model string in LiteLLM format.

    Args:
        provider: The provider name. If None, uses LLM_PROVIDER env var.

    Returns:
        The model string in format "provider/model-name"
    """
    if provider is None:
        provider = get_provider()

    # Check if user specified a custom model
    custom_model = os.getenv("LLM_MODEL")
    if custom_model:
        # If custom_model already has provider prefix, use it as is
        if "/" in custom_model and custom_model.split("/")[0] in DEFAULT_MODELS:
            return custom_model
        # Otherwise, add provider prefix
        return f"{provider}/{custom_model}"

    return DEFAULT_MODELS.get(provider, DEFAULT_MODELS["openai"])


def get_api_key_env(provider: Optional[str] = None) -> str:
    """Get the API key environment variable name for the provider.

    Args:
        provider: The provider name. If None, uses LLM_PROVIDER env var.

    Returns:
        The environment variable name for the API key
    """
    if provider is None:
        provider = get_provider()

    return API_KEY_ENV_VARS.get(provider, "OPENAI_API_KEY")


def get_base_url(provider: Optional[str] = None) -> Optional[str]:
    """Get the base URL for providers that need it (e.g., local models).

    Args:
        provider: The provider name. If None, uses LLM_PROVIDER env var.

    Returns:
        The base URL if applicable, None otherwise
    """
    if provider is None:
        provider = get_provider()

    # Check for custom base URL in env var
    if provider == "local":
        return os.getenv("OLLAMA_BASE_URL", BASE_URLS.get("local"))

    return None


def get_model_info(provider: Optional[str] = None) -> ModelInfo:
    """Get complete model information.

    Args:
        provider: The provider name. If None, uses LLM_PROVIDER env var.

    Returns:
        A ModelInfo dataclass with all configuration details
    """
    if provider is None:
        provider = get_provider()

    model = get_model(provider)
    api_key_env = get_api_key_env(provider)

    # Create a user-friendly display name
    provider_name = provider.capitalize()
    model_name = model.split("/")[-1] if "/" in model else model
    display_name = f"{provider_name} ({model_name})"

    return ModelInfo(
        provider=provider,
        model=model,
        display_name=display_name,
        api_key_env=api_key_env if api_key_env else "",
    )


def validate_config(provider: Optional[str] = None) -> tuple[bool, str]:
    """Validate that the required configuration is present.

    Args:
        provider: The provider name. If None, uses LLM_PROVIDER env var.

    Returns:
        A tuple of (is_valid, error_message)
    """
    if provider is None:
        provider = get_provider()

    if provider not in DEFAULT_MODELS:
        return False, f"Unknown provider: {provider}"

    api_key_env = get_api_key_env(provider)
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            return False, f"API key not found. Please set {api_key_env} environment variable."

    # For local models, check if Ollama is accessible (optional)
    if provider == "local":
        base_url = get_base_url(provider)
        if base_url:
            # Just warn, don't fail - user can start Ollama later
            return True, f"Local model will use: {base_url}"

    return True, "Configuration is valid"


def get_supported_providers() -> list[str]:
    """Get list of all supported providers.

    Returns:
        List of provider names
    """
    return list(DEFAULT_MODELS.keys())
