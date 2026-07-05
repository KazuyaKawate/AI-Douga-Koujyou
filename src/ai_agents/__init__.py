"""AIOS Agent システム。

Factory・Kernel・Router と独立した Agent 管理モジュール。

基本的な使い方:
    from src.ai_agents import get_agent_registry, AgentDefinition, AgentConfig

    registry = get_agent_registry()
    agent = registry.get("writing_specialist")
    print(agent.system_prompt)
"""
from .definition import AgentDefinition, AgentConfig
from .registry import AgentRegistry, get_agent_registry, reset_agent_registry
from .template import AgentTemplate

__all__ = [
    "AgentDefinition",
    "AgentConfig",
    "AgentRegistry",
    "AgentTemplate",
    "get_agent_registry",
    "reset_agent_registry",
]
