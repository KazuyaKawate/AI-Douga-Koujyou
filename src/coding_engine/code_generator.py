from __future__ import annotations

from typing import Any

from src.coding_engine.provider_router import CodingProviderRouter, ProviderResult


class CodeGenerator:
    def __init__(self, provider_router: CodingProviderRouter | None = None) -> None:
        self.provider_router = provider_router or CodingProviderRouter()

    def generate_patch_plan(self, issue: str, plan: dict[str, Any], repository: dict[str, Any]) -> dict[str, Any]:
        prompt = self._prompt(issue, plan, repository)
        result = self.provider_router.complete(
            prompt,
            system_prompt=(
                "You are AIOS Coding Engine. Return concise implementation guidance only. "
                "Prefer revenue speed, low risk, small diffs, tests, and knowledge persistence."
            ),
            retries=2,
        )
        fallback = self._fallback_plan(issue, plan)
        return {
            "provider": result.provider,
            "ok": result.ok,
            "content": result.content.strip() if result.ok else fallback,
            "error": result.error,
            "fallback_used": not result.ok,
        }

    def _prompt(self, issue: str, plan: dict[str, Any], repository: dict[str, Any]) -> str:
        snapshots = []
        for item in repository.get("snapshots", [])[:6]:
            snapshots.append(f"FILE: {item.get('path')}\n{item.get('content', '')[:3000]}")
        return (
            f"Issue:\n{issue}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Relevant repository snapshots:\n\n" + "\n\n".join(snapshots)
        )

    @staticmethod
    def _fallback_plan(issue: str, plan: dict[str, Any]) -> str:
        return (
            "Local heuristic plan: keep the change minimal, update only selected files, "
            "run focused tests plus compileall, then save ROI/review/knowledge records. "
            f"Issue={issue[:240]} Target={plan.get('target_files', [])}"
        )
