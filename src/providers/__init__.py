"""src.providers — local-first provider adapter interfaces."""

from src.providers.base_provider import BaseProvider, ProviderResult, VirtualProvider
from src.providers.gemini_cli_provider import GeminiCLIProvider, GeminiCLIResult
from src.providers.provider_registry import ProviderRegistry, get_provider_registry

__all__ = [
    "BaseProvider",
    "GeminiCLIProvider",
    "GeminiCLIResult",
    "ProviderRegistry",
    "ProviderResult",
    "VirtualProvider",
    "get_provider_registry",
]
