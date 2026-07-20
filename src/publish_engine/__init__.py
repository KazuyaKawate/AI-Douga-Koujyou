from __future__ import annotations

from src.publish_engine.publish_models import PublishPlan
from src.publish_engine.publish_pipeline import PublishPipeline
from src.publish_engine.publish_planner import PublishPlanner
from src.publish_engine.publisher import PublishEngine

__all__ = ["PublishEngine", "PublishEngineGateway", "PublishPipeline", "PublishPlan", "PublishPlanner", "ThreadsPublishingWorkflow"]


def __getattr__(name: str):
    if name == "PublishEngineGateway":
        from src.publish_engine.gateway import PublishEngineGateway

        return PublishEngineGateway
    if name == "ThreadsPublishingWorkflow":
        from src.publish_engine.threads_workflow import ThreadsPublishingWorkflow

        return ThreadsPublishingWorkflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
