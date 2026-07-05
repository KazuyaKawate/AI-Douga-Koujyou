from .base import BaseFactory
from .creator import CreatorFactory
from .fortune import FortuneFactory
from .sns import SNSFactory
from .writing import WritingFactory
from .video import VideoFactory
from .research import ResearchFactory
from .marketing import MarketingFactory
from src.factories.note.factory import NoteFactory

FACTORY_REGISTRY: dict[str, type[BaseFactory]] = {
    "creator":   CreatorFactory,
    "fortune":   FortuneFactory,
    "sns":       SNSFactory,
    "writing":   WritingFactory,
    "video":     VideoFactory,
    "research":  ResearchFactory,
    "marketing": MarketingFactory,
    "note":      NoteFactory,
}

__all__ = [
    "BaseFactory",
    "CreatorFactory",
    "FortuneFactory",
    "SNSFactory",
    "WritingFactory",
    "VideoFactory",
    "ResearchFactory",
    "MarketingFactory",
    "NoteFactory",
    "FACTORY_REGISTRY",
]
