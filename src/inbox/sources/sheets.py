from __future__ import annotations
import json
from pathlib import Path

from ..models import InboxConfig, InboxEntry
from .base import BaseInboxSource

# Google Sheets のカラム定義
_INBOX_COLUMNS  = ["id", "created_at", "source_name", "task_type",
                    "prompt", "status", "processed_at", "priority"]
_OUTBOX_COLUMNS = ["inbox_id", "completed_at", "provider", "model",
                   "response", "input_tokens", "output_tokens", "cost_usd", "error"]


class GoogleSheetsInboxSource(BaseInboxSource):
    """
    Google Sheets をInbox/Outbox として使うソース。

    Inbox シート構造 (Factory_Inbox):
        id | created_at | source_name | task_type | prompt | status | processed_at | priority

    Outbox シート構造 (Factory_Outbox):
        inbox_id | completed_at | provider | model | response
        | input_tokens | output_tokens | cost_usd | error

    実装時の注意:
        - allow_write=False をデフォルトにすること
        - spreadsheet_id は config/workspace_local.json から取得すること
        - credentials は絶対にコードに埋め込まないこと
        - gspread.Worksheet.get_all_records() でポーリングし、
          find() + update_cell() で status を更新する

    将来実装イメージ:
        import gspread
        client = gspread.service_account(filename=credentials_path)
        ss     = client.open_by_key(spreadsheet_id)
        inbox  = ss.worksheet(config.inbox_sheet)
        rows   = inbox.get_all_records()
        pending = [r for r in rows if r["status"] == "pending"][:max_batch]
    """

    INBOX_COLUMNS  = _INBOX_COLUMNS
    OUTBOX_COLUMNS = _OUTBOX_COLUMNS

    def __init__(self, config: InboxConfig) -> None:
        self._config           = config
        self._spreadsheet_id   = self._resolve_spreadsheet_id()
        self._allow_write      = config.allow_write

    # ---- BaseInboxSource 実装 ------------------------------------------

    @property
    def source_name(self) -> str:
        return "google_sheets"

    def is_available(self) -> bool:
        """spreadsheet_id が設定されていれば利用可能とみなす。"""
        return bool(self._spreadsheet_id)

    def fetch_pending(self, max_batch: int) -> list[InboxEntry]:
        """
        スタブ: 将来 gspread でシートから status=pending 行を読み込む。

        実装イメージ:
            ws   = self._get_inbox_ws()
            rows = ws.get_all_records()
            return [self._row_to_entry(r) for r in rows
                    if r.get("status") == "pending"][:max_batch]
        """
        return []

    def mark_processing(self, entry_id: str) -> None:
        """
        スタブ: 将来 status 列を "processing" に更新する。

        実装イメージ:
            ws   = self._get_inbox_ws()
            cell = ws.find(entry_id)
            ws.update_cell(cell.row, ws.find("status").col, "processing")
        """
        if not self._allow_write:
            print(f"[dry-run] GoogleSheets.mark_processing: {entry_id}")

    def mark_done(self, entry_id: str) -> None:
        """スタブ: 将来 status 列を "done" に更新する。"""
        if not self._allow_write:
            print(f"[dry-run] GoogleSheets.mark_done: {entry_id}")

    def mark_error(self, entry_id: str, message: str) -> None:
        """スタブ: 将来 status 列を "error" に更新し、エラーメッセージを記録する。"""
        if not self._allow_write:
            print(f"[dry-run] GoogleSheets.mark_error: {entry_id} - {message}")

    # ---- Private -------------------------------------------------------

    def _resolve_spreadsheet_id(self) -> str:
        """config/workspace_local.json の spreadsheet_id を取得する。"""
        local_file = Path("config/workspace_local.json")
        if local_file.exists():
            try:
                data = json.loads(local_file.read_text(encoding="utf-8"))
                sid = data.get("spreadsheet_id", "")
                if isinstance(sid, str) and sid:
                    return sid
            except Exception:
                pass
        return ""
