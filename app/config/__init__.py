"""
Configuration module for the TCSRS application.
"""
from .prompts import DEFAULT_AI_PROMPTS, CARD_FORMAT_PROMPT
from .ai_providers import (
    AI_PROVIDERS,
    AIProvider,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    get_default_model,
    get_provider_display_name,
    get_provider_env_key,
    get_all_providers,
)

__all__ = [
    "DEFAULT_AI_PROMPTS",
    "CARD_FORMAT_PROMPT",
    "AI_PROVIDERS",
    "AIProvider",
    "DEFAULT_PROVIDER",
    "DEFAULT_MODEL",
    "get_default_model",
    "get_provider_display_name",
    "get_provider_env_key",
    "get_all_providers",
]
