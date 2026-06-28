from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from .enums import WorkflowState
from .models import WorkflowStatus

_DEFAULT_STORE_DIR = Path("data/workflows")


class WorkflowStore:
    """
    WorkflowStatus を data/workflows/{workflow_id}.json に永続化する。

    Dashboard や外部プロセスが別プロセスから実行状態を読める。
    スレッドセーフではない（WorkflowRunner が1インスタンス1ファイルを担当する想定）。
    書き込み失敗は例外を投げず無視する（Dashboard 不可でもワークフローを止めない）。
    """

    def __init__(self, store_dir: Path = _DEFAULT_STORE_DIR) -> None:
        self._dir = store_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, status: WorkflowStatus) -> None:
        try:
            path = self._dir / f"{status.workflow_id}.json"
            path.write_text(
                json.dumps(status.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def load(self, workflow_id: str) -> Optional[WorkflowStatus]:
        path = self._dir / f"{workflow_id}.json"
        if not path.exists():
            return None
        try:
            return WorkflowStatus.from_dict(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception:
            return None

    def list_all(self) -> list[WorkflowStatus]:
        result: list[WorkflowStatus] = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                result.append(
                    WorkflowStatus.from_dict(json.loads(p.read_text(encoding="utf-8")))
                )
            except Exception:
                continue
        return result

    def list_by_state(self, state: WorkflowState) -> list[WorkflowStatus]:
        return [s for s in self.list_all() if s.state == state]

    def delete(self, workflow_id: str) -> bool:
        path = self._dir / f"{workflow_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
