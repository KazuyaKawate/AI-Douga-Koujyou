from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.path_safety import safe_resolve_path, workspace_relative_path


class CodeEditor:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)

    def propose_edits(self, issue: str, plan: dict[str, Any], generated: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "type": "manual_required",
                "path": path,
                "reason": "Coding Engine created the execution plan. File mutation requires a concrete patch operation.",
                "guidance": generated.get("content", "")[:1200],
            }
            for path in plan.get("target_files", [])[:10]
        ]

    def apply_generated_patch(
        self,
        generated: dict[str, Any],
        *,
        approved: bool = False,
        target_files: list[str] | None = None,
        risks: list[str] | None = None,
        test_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        patch = self._extract_unified_diff(str(generated.get("content", "")))
        if not patch:
            return {"applied": False, "status": "no_patch", "message": "No unified diff found."}
        preview = {
            "unified_diff": patch[:20000],
            "target_files": target_files or [],
            "risks": risks or [],
            "test_plan": test_plan or {},
            "requires_approval": True,
        }
        check = self._git_apply(patch, check=True)
        if not check.get("ok"):
            return {"applied": False, "status": "check_failed", "preview": preview, **check}
        if not approved:
            return {
                "applied": False,
                "status": "preview_locked",
                "message": "Unified diff is valid, but explicit approval is required before apply.",
                "preview": preview,
                "check": check,
            }
        result = self._git_apply(patch, check=False)
        return {"applied": result.get("ok", False), "status": "applied" if result.get("ok") else "failed", "preview": preview, **result}

    def replace_text(self, relative_path: str, old: str, new: str) -> dict[str, Any]:
        path = safe_resolve_path(self.root, relative_path)
        before = path.read_text(encoding="utf-8")
        if old not in before:
            return {"ok": False, "path": relative_path, "error": "old text not found"}
        path.write_text(before.replace(old, new, 1), encoding="utf-8")
        return {"ok": True, "path": str(workspace_relative_path(self.root, path)).replace("\\", "/")}

    def write_file(self, relative_path: str, content: str, *, overwrite: bool = False) -> dict[str, Any]:
        path = safe_resolve_path(self.root, relative_path)
        if path.exists() and not overwrite:
            return {"ok": False, "path": relative_path, "error": "file exists"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(workspace_relative_path(self.root, path)).replace("\\", "/")}

    def _git_apply(self, patch: str, *, check: bool) -> dict[str, Any]:
        command = ["git", "apply", "--check"] if check else ["git", "apply"]
        try:
            completed = subprocess.run(
                command,
                input=patch,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=30,
                shell=False,
            )
            return {
                "ok": completed.returncode == 0,
                "command": " ".join(command),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except Exception as exc:
            return {"ok": False, "command": " ".join(command), "stdout": "", "stderr": str(exc)}

    @staticmethod
    def _extract_unified_diff(content: str) -> str:
        if "```" in content:
            blocks = content.split("```")
            for block in blocks:
                candidate = block.removeprefix("diff").strip()
                if candidate.startswith("diff --git ") or candidate.startswith("--- "):
                    return candidate + "\n"
        stripped = content.strip()
        if stripped.startswith("diff --git ") or stripped.startswith("--- "):
            return stripped + "\n"
        return ""
