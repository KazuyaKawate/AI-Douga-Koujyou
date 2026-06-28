from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class TaskType(str, Enum):
    CODING      = "coding"
    REVIEW      = "review"
    PLANNING    = "planning"
    ANALYSIS    = "analysis"
    WRITING     = "writing"
    TRANSLATION = "translation"
    VISION      = "vision"
    DEFAULT     = "default"


@dataclass
class AITask:
    task_type: TaskType
    prompt: str
    system_prompt: str | None = None
    context: list[dict] | None = None
    options: dict | None = field(default=None)
