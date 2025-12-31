"""
AI Provider configurations for card generation.
Defines available AI providers, their models, and helper functions.
"""
from typing import Dict, List, Literal

# AI Provider type
AIProvider = Literal["openai", "google", "xai", "anthropic"]


# AI Provider configuration structure
AI_PROVIDERS: Dict[str, Dict] = {
    "openai": {
        "display_name": "OpenAI",
        "models": [
            {"id": "gpt-5.2", "name": "GPT-5.2"},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini"},
            {"id": "gpt-5-nano", "name": "GPT-5 Nano"},
            {"id": "gpt-4.1", "name": "GPT-4.1"},
        ],
        "env_key": "OPENAI_API_KEY",
    },
    "google": {
        "display_name": "Google",
        "models": [
            {"id": "gemini-3-pro-review", "name": "Gemini 3 Pro"},
            {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash Pro"},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite"},
        ],
        "env_key": "GOOGLE_API_KEY",
    },
    "xai": {
        "display_name": "xAI",
        "models": [
            {"id": "grok-4-1-fast-reasoning", "name": "Grok 4.1 Fast Reasoning"},
            {"id": "grok-4-1-fast-non-reasoning", "name": "Grok 4.1 Fast Non-Reasoning"},
        ],
        "env_key": "XAI_API_KEY",
    },
    "anthropic": {
        "display_name": "Anthropic",
        "models": [
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
            {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5"},
            {"id": "claude-opus-4-5", "name": "Claude Opus 4.5"},
        ],
        "env_key": "ANTHROPIC_API_KEY",
    },
}

DEFAULT_PROVIDER: AIProvider = "openai"
DEFAULT_MODEL = "gpt-5.2"


def get_default_model(provider: str) -> str:
    """Get the default model for a given provider."""
    provider_config = AI_PROVIDERS.get(provider)
    if provider_config and provider_config["models"]:
        return provider_config["models"][0]["id"]
    return ""


def get_provider_display_name(provider: str) -> str:
    """Get the display name for a provider."""
    provider_config = AI_PROVIDERS.get(provider)
    return provider_config["display_name"] if provider_config else provider


def get_provider_env_key(provider: str) -> str:
    """Get the environment variable name for a provider's API key."""
    provider_config = AI_PROVIDERS.get(provider)
    return provider_config["env_key"] if provider_config else ""


def get_all_providers() -> List[str]:
    """Get list of all available provider names."""
    return list(AI_PROVIDERS.keys())
