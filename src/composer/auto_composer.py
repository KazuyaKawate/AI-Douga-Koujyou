"""AutoAgentComposer — 目的語から既存 Agent を組み合わせて Workflow を自動生成する。

from src.utils.json_store import save_json_atomic
Kernel / Router / Memory を変更しない。
AIRouter を直接呼び出してプランニングに使用する。
生成した WorkflowDefinition を kernel.registry にホット登録する。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_COMPOSED_DIR = Path("data/intelligence/composed_workflows")


@dataclass
class ComposedWorkflow:
    """AutoComposer の生成結果。"""
    goal:          str
    workflow_name: str
    description:   str
    step_count:    int
    agent_ids:     list[str] = field(default_factory=list)
    workflow_json: str = ""
    saved_path:    Optional[Path] = None
    registered:    bool = False
    error:         Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class AutoAgentComposer:
    """
    ユーザーの「目的」から Workflow を自動生成して即時登録する。

    手順:
        1. AgentRegistry から利用可能な Agent 一覧を取得
        2. 既存 Workflow 一覧を取得
        3. AI (Router 経由) に Workflow JSON の設計を依頼
        4. JSON をパースして WorkflowDefinition を構築
        5. kernel.registry にホット登録 + JSON ファイルに保存

    使い方:
        composer = AutoAgentComposer()
        result   = composer.compose("YouTubeを伸ばしたい")
        if result.success:
            print(result.workflow_name)
    """

    def compose(self, goal: str, workflow_prefix: str = "composed") -> ComposedWorkflow:
        """目的から Workflow を生成して登録する。"""
        try:
            # 利用可能リソースを収集
            available_agents    = self._get_available_agents()
            available_workflows = self._get_available_workflows()
            available_factories = self._get_available_factories()

            # AI にプランニングを依頼
            plan_json = self._plan_with_ai(
                goal, available_agents, available_workflows, available_factories
            )

            # JSON をパース
            plan = self._parse_plan(plan_json, goal, workflow_prefix)

            # WorkflowDefinition を構築・登録
            wf_def = self._build_workflow_definition(plan)

            # ホット登録
            from src.core.kernel import get_kernel
            get_kernel().registry.register_workflow(wf_def)

            # ファイル保存
            _COMPOSED_DIR.mkdir(parents=True, exist_ok=True)
            safe_name  = wf_def.name.replace(".", "_").replace("/", "_")
            saved_path = _COMPOSED_DIR / f"{safe_name}.json"
            wf_dict    = wf_def.to_dict() if hasattr(wf_def, "to_dict") else {}
            save_json_atomic(saved_path, wf_dict)

            agent_ids = [
                step.get("config", {}).get("agent_id", "")
                for step in plan.get("steps", [])
                if step.get("step_type") == "ai_task"
            ]

            return ComposedWorkflow(
                goal          = goal,
                workflow_name = wf_def.name,
                description   = plan.get("description", ""),
                step_count    = len(plan.get("steps", [])),
                agent_ids     = [a for a in agent_ids if a],
                workflow_json = json.dumps(wf_dict, ensure_ascii=False, indent=2),
                saved_path    = saved_path,
                registered    = True,
            )

        except Exception as exc:
            return ComposedWorkflow(
                goal=goal,
                workflow_name="",
                description="",
                step_count=0,
                error=str(exc),
            )

    # ---- Private: AI planning ---------------------------------------

    def _plan_with_ai(
        self,
        goal:       str,
        agents:     list[dict],
        workflows:  list[str],
        factories:  list[str],
    ) -> str:
        """AI Router 経由で Workflow JSON を生成する。"""
        from src.ai.router import get_router

        agent_summary = "\n".join(
            f"- {a['agent_id']}: {a.get('description','')[:60]} "
            f"[role={a.get('role','')}, task_type={a.get('task_type','')}]"
            for a in agents[:30]
        )

        prompt = f"""あなたは AIOS Workflow 設計の専門家です。
ユーザーの目的を達成するための Workflow を JSON で設計してください。

【ユーザーの目的】
{goal}

【利用可能な Agent (agent_id: 説明)】
{agent_summary}

【利用可能な Factory】
{', '.join(factories)}

【Workflow JSON の仕様】
{{
  "name": "composed.{'{'}short_english_name{'}'}",
  "description": "目的の説明（日本語）",
  "version": "1.0.0",
  "steps": [
    {{
      "step_id": "step_1",
      "step_type": "ai_task",
      "name": "ステップ名（日本語）",
      "depends_on": [],
      "config": {{
        "task_type": "writing|analysis|general",
        "output_key": "step1_output",
        "prompt": "このステップのプロンプト。{{topic}} などのコンテキスト変数を使える。"
      }},
      "retry_max": 1,
      "on_failure": "continue"
    }},
    {{
      "step_id": "step_2",
      "step_type": "memory_update",
      "name": "結果保存",
      "depends_on": ["step_1"],
      "config": {{
        "key": "last_result",
        "value_from_context": "step1_output",
        "scope": "global"
      }},
      "on_failure": "continue"
    }}
  ]
}}

【設計ルール】
- step_id は step_1, step_2 ... と連番にする
- depends_on は先行 step_id の配列
- ai_task ステップは2〜5個程度
- 最後のステップは必ず memory_update で結果を保存する
- on_failure は必ず "continue" または "abort" を指定する
- 必ず上記の JSON 仕様に厳密に従う

目的「{goal}」を達成する Workflow JSON のみ出力してください（```json ブロックで囲む）。"""

        from src.ai.task import AITask, TaskType
        task = AITask(task_type=TaskType.DEFAULT, prompt=prompt)
        resp = get_router().route(task)
        return resp.content if resp and resp.ok else ""

    def _parse_plan(
        self, ai_response: str, goal: str, prefix: str
    ) -> dict:
        """AI レスポンスから JSON を抽出・パースする。"""
        # ```json ... ``` ブロックを探す
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", ai_response, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # ブロックなしでも { から } を探す
            start = ai_response.find("{")
            end   = ai_response.rfind("}")
            if start != -1 and end != -1:
                json_str = ai_response[start:end + 1]
            else:
                raise ValueError("AI response に有効な JSON が含まれていません")

        plan = json.loads(json_str)

        # name を強制的に composed. プレフィックスにする
        if not plan.get("name", "").startswith("composed."):
            safe_goal = re.sub(r"[^\w]", "_", goal[:20]).strip("_").lower()
            ts        = datetime.now().strftime("%m%d%H%M")
            plan["name"] = f"composed.{safe_goal}_{ts}"

        return plan

    def _build_workflow_definition(self, plan: dict):
        """plan dict から WorkflowDefinition を構築する。"""
        from src.workflow.models import WorkflowDefinition
        return WorkflowDefinition.from_dict(plan)

    # ---- Private: リソース収集 --------------------------------------

    def _get_available_agents(self) -> list[dict]:
        try:
            from src.ai_agents.registry import get_agent_registry
            agents = get_agent_registry().list_all(enabled_only=True)
            return [
                {
                    "agent_id":    a.agent_id,
                    "description": a.description,
                    "role":        a.role,
                    "task_type":   a.task_type,
                    "capabilities":a.capabilities,
                }
                for a in agents
            ]
        except Exception:
            return []

    def _get_available_workflows(self) -> list[str]:
        try:
            from src.core.kernel import get_kernel
            return get_kernel().registry.list_workflows()
        except Exception:
            return []

    def _get_available_factories(self) -> list[str]:
        try:
            from src.core.kernel import get_kernel
            return get_kernel().registry.list_factories()
        except Exception:
            return []

    def list_composed(self) -> list[Path]:
        """保存済みの composed workflow ファイル一覧を返す。"""
        if not _COMPOSED_DIR.exists():
            return []
        return sorted(_COMPOSED_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

