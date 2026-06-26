"""OpenAI provider — wraps ai_pipeline for script generation."""
from src.utils.config import OPENAI_API_KEY

NAME     = "OpenAI"
IS_MANUAL = False


def is_available() -> bool:
    return bool(OPENAI_API_KEY)


def generate_script(topic: str, episode_id: str, **kwargs) -> tuple[dict, dict]:
    """Generate episode script via OpenAI. Returns (episode, written_files)."""
    from src.core import ai_pipeline
    return ai_pipeline.generate_episode_ai(
        topic=topic,
        episode_id=episode_id,
        **kwargs,
    )
