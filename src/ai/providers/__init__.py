from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .virtual_provider import VirtualAgentProvider

PROVIDER_REGISTRY: dict[str, type] = {
    "openai":   OpenAIProvider,
    "claude":   ClaudeProvider,
    "gemini":   GeminiProvider,
    "virtual":  VirtualAgentProvider,
}

__all__ = [
    "OpenAIProvider", "ClaudeProvider", "GeminiProvider",
    "VirtualAgentProvider", "PROVIDER_REGISTRY",
]
