"""note投稿工場 — Article management, scoring, revenue, repurposing.

Note Factory Executor を EXECUTOR_REGISTRY に登録する。
このモジュールが import されることで登録が完了する。
"""
from src.workflow.executors import EXECUTOR_REGISTRY
from src.factories.note.executors import (
    NoteIdeaExecutor,
    NotePlanExecutor,
    NoteWriteExecutor,
    NoteReviewExecutor,
    NotePublishExecutor,
    NoteAnalyzeExecutor,
    NoteMemoryExecutor,
)

EXECUTOR_REGISTRY.update({
    "note_idea":    NoteIdeaExecutor,
    "note_plan":    NotePlanExecutor,
    "note_write":   NoteWriteExecutor,
    "note_review":  NoteReviewExecutor,
    "note_publish": NotePublishExecutor,
    "note_analyze": NoteAnalyzeExecutor,
    "note_memory":  NoteMemoryExecutor,
})
