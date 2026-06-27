"""command_preview — Generate human-readable previews of pending actions.

Read-only. Never executes commands.
"""
from __future__ import annotations

_SOURCE_INTROS = {
    "aiceo":      "AI CEO Coreが推奨するアクション:",
    "automation": "自動化工場が要求するワークフロー:",
    "devstudio":  "Development Studioからの決定リクエスト:",
    "manual":     "手動リクエスト:",
}

_RISK_WARNINGS = {
    "high":   "⚠️ 高リスク — 元に戻せない可能性があります。慎重に判断してください。",
    "medium": "🟠 中リスク — 内容を確認してから承認してください。",
    "low":    "🟡 低リスク — 軽微な変更です。",
    "none":   "🟢 リスクなし — 読み取り専用または安全な操作です。",
}


def preview_action(item: dict) -> str:
    """Return a multi-line human-readable preview of what this action does."""
    source = item.get("source", "manual")
    intro = _SOURCE_INTROS.get(source, "リクエスト:")
    risk = item.get("estimated_risk", "low")
    warning = _RISK_WARNINGS.get(risk, "")

    lines = [
        f"### {item.get('title', '(タイトルなし)')}",
        "",
        f"**ソース**: {_SOURCE_INTROS.get(source, source)}",
        "",
        f"**実行内容**:",
        f"> {item.get('command_summary', '(詳細なし)')}",
        "",
        f"**期待される効果**:",
        f"> {item.get('expected_impact', '(記載なし)')}",
    ]

    affected = item.get("affected_files", [])
    if affected:
        lines += ["", "**影響ファイル**:"]
        for f in affected[:10]:
            lines.append(f"- `{f}`")
        if len(affected) > 10:
            lines.append(f"- …他 {len(affected) - 10} 件")

    notes = item.get("notes", "")
    if notes:
        lines += ["", f"**備考**: {notes}"]

    if warning:
        lines += ["", warning]

    return "\n".join(lines)


def get_short_summary(item: dict) -> str:
    """Return a single-line summary suitable for a list view."""
    risk_icon = {"none": "🟢", "low": "🟡", "medium": "🟠", "high": "🔴"}.get(
        item.get("estimated_risk", "low"), "⚪"
    )
    source_label = {
        "aiceo": "AI CEO", "automation": "自動化", "devstudio": "DevStudio", "manual": "手動"
    }.get(item.get("source", "manual"), "不明")
    return f"{risk_icon} [{source_label}] {item.get('title', '(タイトルなし)')}"


def get_affected_files(item: dict) -> list[str]:
    return item.get("affected_files", [])


def format_for_export(item: dict) -> str:
    """Return a concise text block for export/reporting."""
    created = item.get("created_at", "")[:10]
    status = item.get("status", "pending")
    risk = item.get("estimated_risk", "low")
    return (
        f"[{status.upper()}] {item.get('title', '')} "
        f"(作成: {created}, リスク: {risk}, ソース: {item.get('source', '')})\n"
        f"  内容: {item.get('command_summary', '')}\n"
        f"  効果: {item.get('expected_impact', '')}"
    )
