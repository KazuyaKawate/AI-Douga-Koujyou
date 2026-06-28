"""
Project Snapshot — AI引き継ぎ・コンテキスト復元用スナップショット。

SnapshotBuilder : 現在の状態を JSON として出力
SnapshotLoader  : JSON からワークスペースを復元（validate → restore）
"""
from __future__ import annotations
import datetime
import json
import subprocess
import uuid
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
SNAPSHOT_DIR   = Path("snapshots")
HISTORY_DIR    = SNAPSHOT_DIR / "history"
LATEST_PATH    = SNAPSHOT_DIR / "latest.json"


class SnapshotValidationError(Exception):
    """スナップショット検証失敗時に送出する。"""


# ---- Builder ----------------------------------------------------------

class SnapshotBuilder:
    """
    現在のプロジェクト状態を JSON スナップショットとして構築・保存する。

    Usage:
        builder  = SnapshotBuilder(router=router, memory=memory, logger=logger)
        snapshot = builder.build()
        path     = builder.save()
    """

    def __init__(
        self,
        router=None,
        memory=None,
        logger=None,
        config_path: Path = Path("config/ai_router.json"),
        workspace_local_path: Path = Path("config/workspace_local.json"),
    ) -> None:
        self._router               = router
        self._memory               = memory
        self._logger               = logger
        self._config_path          = config_path
        self._workspace_local_path = workspace_local_path

    def build(self) -> dict:
        """全セクションを組み立てて dict を返す。副作用なし。"""
        return {
            "schema_version":    SCHEMA_VERSION,
            "snapshot_id":       str(uuid.uuid4()),
            "created_at":        datetime.datetime.now().isoformat(timespec="seconds"),
            "meta":              self._section_meta(),
            "project":           self._section_project(),
            "git":               self._section_git(),
            "current_work":      self._section_current_work(),
            "ai_router":         self._section_ai_router(),
            "workspace_memory":  self._section_memory(),
            "router_logger":     self._section_router_logger(),
            "sheets_logger":     self._section_sheets_logger(),
            "config":            self._section_config(),
        }

    def save(self, extra_path: Path | None = None) -> Path:
        """
        snapshots/latest.json を上書き保存し、history/ にも記録する。
        extra_path が指定された場合はそちらにも保存する。
        """
        content = json.dumps(self.build(), ensure_ascii=False, indent=2)

        SNAPSHOT_DIR.mkdir(exist_ok=True)
        LATEST_PATH.write_text(content, encoding="utf-8")

        HISTORY_DIR.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        (HISTORY_DIR / f"snapshot_{ts}.json").write_text(content, encoding="utf-8")

        if extra_path is not None:
            extra_path.write_text(content, encoding="utf-8")

        return LATEST_PATH

    # ---- セクション構築 -----------------------------------------------

    def _section_meta(self) -> dict:
        return {
            "purpose":         "AI引き継ぎ・コンテキスト復元用スナップショット",
            "instructions_ja": (
                "current_work.next_task から作業を再開してください。"
                "api_key は REDACTED のため workspace_local.json から取得してください。"
            ),
            "instructions_en": (
                "Resume from current_work.next_task. "
                "API keys are REDACTED; read from workspace_local.json."
            ),
            "generated_by":  f"ProjectSnapshot v{SCHEMA_VERSION}",
            "ai_compatible": ["claude", "openai", "gemini"],
        }

    def _section_project(self) -> dict:
        return {
            "name":        "Creator Factory OS",
            "version":     "5.2-beta",
            "description": "Streamlit multi-page app, Python, local-first, 27 pages",
        }

    def _section_git(self) -> dict:
        try:
            log = subprocess.run(
                ["git", "log", "-1", "--format=%H\x1f%D\x1f%s\x1f%ci"],
                capture_output=True, text=True, check=True, encoding="utf-8",
            )
            parts = log.stdout.strip().split("\x1f")
            commit  = parts[0][:8]      if len(parts) > 0 else ""
            ref     = parts[1]          if len(parts) > 1 else ""
            message = parts[2]          if len(parts) > 2 else ""
            date    = parts[3].strip()  if len(parts) > 3 else ""

            branch = ""
            for token in ref.split(","):
                token = token.strip()
                if token.startswith("HEAD ->"):
                    branch = token.replace("HEAD ->", "").strip()
                    break
            if not branch:
                r = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True, text=True, check=False, encoding="utf-8",
                )
                branch = r.stdout.strip()

            dirty = bool(subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, check=False, encoding="utf-8",
            ).stdout.strip())

            return {
                "commit":         commit,
                "branch":         branch,
                "commit_message": message,
                "committed_at":   date,
                "dirty":          dirty,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _section_current_work(self) -> dict:
        if self._memory is None:
            return {"epic": "", "task": "", "next_task": "", "status": "", "notes": ""}

        from .memory import MemoryKey, MemoryScope

        def _mg(key: MemoryKey) -> str:
            return (
                self._memory.get(key.value, MemoryScope.GLOBAL)
                or self._memory.get(key.value, MemoryScope.PROJECT)
                or ""
            )

        return {
            "epic":      _mg(MemoryKey.CURRENT_PHASE),
            "task":      _mg(MemoryKey.CURRENT_TASK),
            "next_task": _mg(MemoryKey.PENDING_TASK),
            "status":    "in_progress",
            "notes":     _mg(MemoryKey.IMPORTANT_NOTES),
        }

    def _section_ai_router(self) -> dict:
        if self._router is None:
            return {"error": "router not provided"}

        hc = self._router.health_check()

        last_prov  = ""
        last_model = ""
        if self._memory is not None:
            from .memory import MemoryKey, MemoryScope
            last_prov  = self._memory.get(MemoryKey.LAST_PROVIDER.value, MemoryScope.GLOBAL) or ""
            last_model = self._memory.get(MemoryKey.LAST_MODEL.value,    MemoryScope.GLOBAL) or ""

        try:
            task_routing = json.loads(
                self._config_path.read_text(encoding="utf-8")
            ).get("task_routing", {})
        except Exception:
            task_routing = {}

        return {
            "config_version":   hc.get("router_version", ""),
            "default_provider": hc.get("default_provider", ""),
            "last_provider":    last_prov,
            "last_model":       last_model,
            "task_routing":     task_routing,
            "providers":        hc.get("providers", {}),
        }

    def _section_memory(self) -> dict:
        if self._memory is None:
            return {"provider_type": "None", "entry_count": 0, "entries": []}

        entries = self._memory.get_all()
        return {
            "provider_type": type(self._memory).__name__,
            "entry_count":   len(entries),
            "entries": [
                {
                    "key":        e.key,
                    "value":      e.value,
                    "scope":      e.scope.value,
                    "ttl":        e.ttl.value,
                    "version":    e.version,
                    "updated_at": e.updated_at.isoformat(timespec="seconds"),
                }
                for e in entries
            ],
        }

    def _section_router_logger(self) -> dict:
        if self._logger is None:
            return {"type": "None", "configured": False}
        return {
            "type":       type(self._logger).__name__,
            "configured": type(self._logger).__name__ != "NullLogger",
        }

    def _section_sheets_logger(self) -> dict:
        from .logger import SheetsRouterLogger
        return {
            "type":           "SheetsRouterLogger",
            "configured":     False,
            "spreadsheet_id": None,
            "sheets": {
                SheetsRouterLogger.SHEET_REQUESTS:  SheetsRouterLogger.COLUMNS_REQUESTS,
                SheetsRouterLogger.SHEET_LOGS:      SheetsRouterLogger.COLUMNS_LOGS,
                SheetsRouterLogger.SHEET_DECISIONS: SheetsRouterLogger.COLUMNS_DECISIONS,
                SheetsRouterLogger.SHEET_MEMORY:    SheetsRouterLogger.COLUMNS_MEMORY,
            },
        }

    def _section_config(self) -> dict:
        try:
            ai_cfg: dict = json.loads(self._config_path.read_text(encoding="utf-8"))
        except Exception:
            ai_cfg = {}

        ws_cfg: dict = {}
        if self._workspace_local_path.exists():
            try:
                ws_cfg = json.loads(self._workspace_local_path.read_text(encoding="utf-8"))
                if "ai_keys" in ws_cfg:
                    ws_cfg = {**ws_cfg, "ai_keys": "*** REDACTED ***"}
            except Exception:
                ws_cfg = {"error": "読み込み失敗"}

        return {
            "ai_router_path":        str(self._config_path),
            "ai_router":             ai_cfg,
            "workspace_local_path":  str(self._workspace_local_path),
            "workspace_local":       ws_cfg,
        }


# ---- Loader -----------------------------------------------------------

class SnapshotLoader:
    """
    スナップショットからワークスペースを復元するローダー。

    使用手順:
        loader   = SnapshotLoader()
        snapshot = loader.load(path)    # ファイル読み込み（副作用なし）
        loader.validate(snapshot)       # 復元前に必ず検証
        loader.restore(snapshot)        # 将来実装: ワークスペース復元
    """

    SUPPORTED_VERSIONS: set[str] = {"1.0.0"}

    REQUIRED_KEYS: list[str] = [
        "schema_version",
        "snapshot_id",
        "created_at",
        "meta",
        "project",
        "git",
        "current_work",
        "ai_router",
        "workspace_memory",
        "router_logger",
        "sheets_logger",
        "config",
    ]

    def load(self, path: Path) -> dict:
        """
        スタブ: JSON ファイルを読み込んで dict を返す。副作用なし。

        将来実装イメージ:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.validate(data)
            return data
        """
        return {}

    def validate(self, snapshot: dict) -> None:
        """
        スナップショットの整合性を検証する。restore() の前に必ず呼ぶこと。

        検証内容:
            1. 必須キー確認
            2. schema_version が対応バージョンかどうか
            3. 破損チェック（主要セクションの型確認）

        Raises:
            SnapshotValidationError: 検証失敗時
        """
        # 1. 必須キー確認
        missing = [k for k in self.REQUIRED_KEYS if k not in snapshot]
        if missing:
            raise SnapshotValidationError(f"必須キーが不足しています: {missing}")

        # 2. schema_version 確認
        version = snapshot.get("schema_version", "")
        if version not in self.SUPPORTED_VERSIONS:
            raise SnapshotValidationError(
                f"非対応の schema_version: {version!r}  "
                f"対応バージョン: {sorted(self.SUPPORTED_VERSIONS)}"
            )

        # 3. 破損チェック（主要セクションの型確認）
        type_checks: list[tuple[str, type]] = [
            ("meta",             dict),
            ("git",              dict),
            ("current_work",     dict),
            ("ai_router",        dict),
            ("workspace_memory", dict),
        ]
        for key, expected in type_checks:
            if not isinstance(snapshot.get(key), expected):
                raise SnapshotValidationError(
                    f"'{key}' の型が不正です（期待: {expected.__name__}）"
                )

    def restore(self, snapshot: dict) -> None:
        """
        スタブ: スナップショットからワークスペースを復元する。

        復元前に validate() を強制実行する。

        将来の復元順序（依存関係を考慮）:
            1. validate(snapshot)           ← このメソッド内で強制
            2. config       → ai_router.json を snapshot の値で確認
            3. ai_router    → task_routing / providers を Router に反映
            4. workspace_memory → entries を scope / ttl ごとに set()
            5. current_work → epic / task / next_task を memory.set()
            6. logger       → SheetsLogger の spreadsheet_id を再設定
        """
        self.validate(snapshot)
        # スタブ: 将来の復元処理をここに実装する
