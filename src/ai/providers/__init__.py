from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider

PROVIDER_REGISTRY: dict[str, type] = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
}

__all__ = ["OpenAIProvider", "ClaudeProvider", "GeminiProvider", "PROVIDER_REGISTRY"]
