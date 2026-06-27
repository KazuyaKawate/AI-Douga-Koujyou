"""automation_reporter — log runs and export automation reports."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT         = Path(__file__).parent.parent.parent.parent
RUNS_PATH    = ROOT / "config" / "automation_runs.json"
REPORTS_DIR  = ROOT / "reports" / "automation"
MAX_RUNS     = 200


# ── Run log persistence ────────────────────────────────────────────────────────

def load_runs() -> dict:
    if RUNS_PATH.exists():
        try:
            return json.loads(RUNS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"runs": [], "meta": {"version": "4.8", "max_runs": MAX_RUNS}}


def _save_runs(data: dict) -> None:
    RUNS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def log_run(run_record: dict) -> None:
    data = load_runs()
    data["runs"].append(run_record)
    if len(data["runs"]) > MAX_RUNS:
        data["runs"] = data["runs"][-MAX_RUNS:]
    _save_runs(data)


def get_run_history(workflow_id: str | None = None, limit: int = 50) -> list[dict]:
    runs = load_runs().get("runs", [])
    if workflow_id:
        runs = [r for r in runs if r.get("workflow_id") == workflow_id]
    return list(reversed(runs[-limit:]))


def get_run_summary() -> dict:
    runs  = load_runs().get("runs", [])
    total = len(runs)
    fired = sum(1 for r in runs if r.get("trigger_fired"))
    done  = sum(1 for r in runs if r.get("success") and r.get("trigger_fired"))
    dry   = sum(1 for r in runs if r.get("dry_run"))
    last  = runs[-1]["timestamp"] if runs else "—"
    return {
        "total_runs":    total,
        "triggered":     fired,
        "successful":    done,
        "dry_run_count": dry,
        "real_count":    total - dry,
        "last_run":      last,
    }


# ── Report generation ──────────────────────────────────────────────────────────

def generate_automation_report(
    runs: list[dict],
    workflow_summary: dict,
    run_summary: dict,
) -> str:
    ts = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    lines = [
        f"# Automation Report — {datetime.now().strftime('%Y-%m-%d')}",
        f"生成日時: {ts}  |  Creator Factory OS v4.8",
        "",
        "---",
        "",
        "## オートメーションサマリー",
        "",
        "| 項目 | 値 |",
        "|------|---|",
        f"| ワークフロー数 | {workflow_summary['total']} |",
        f"| 有効ワークフロー | {workflow_summary['enabled']} |",
        f"| 総実行回数 | {run_summary['total_runs']} |",
        f"| トリガー発火 | {run_summary['triggered']} |",
        f"| 成功アクション | {run_summary['successful']} |",
        f"| ドライラン実行 | {run_summary['dry_run_count']} |",
        f"| 実際の実行 | {run_summary['real_count']} |",
        f"| 最終実行 | {run_summary['last_run']} |",
        "",
        "---",
        "",
        "## 直近の実行ログ",
        "",
    ]
    if runs:
        lines += ["| 日時 | ワークフロー | トリガー | アクション | ドライラン |",
                  "|------|-------------|---------|-----------|----------|"]
        for r in runs[:20]:
            triggered = "✅" if r.get("trigger_fired") else "—"
            action    = r.get("action_result", {})
            action_str = action.get("description", "—")[:40] if action else "—"
            dry_str   = "DRY" if r.get("dry_run") else "REAL"
            ts_short  = r.get("timestamp", "")[:16].replace("T", " ")
            lines.append(
                f"| {ts_short} | {r.get('workflow_name', '')[:20]} "
                f"| {triggered} {r.get('trigger_reason', '')[:20]} "
                f"| {action_str} | {dry_str} |"
            )
    else:
        lines.append("実行ログはありません。")
    lines += [
        "",
        "---",
        "",
        "## 安全性ノート",
        "",
        "- 全アクションはドラフト作成のみ（published/confirmed ステータスは自動設定しない）",
        "- 外部APIは使用していません",
        "- 既存データの上書きは行いません",
        f"- ドライランモード: デフォルト有効",
        "",
        "---",
        f"*Creator Factory OS Automation Factory v4.8*",
    ]
    return "\n".join(lines)


def export_automation_report(content: str, date_str: str = "") -> Path:
    """Write report to reports/automation/YYYY-MM-DD_automation_report.md."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{date_str or datetime.now().strftime('%Y-%m-%d')}_automation_report.md"
    path     = REPORTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path


def list_reports() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("*_automation_report.md"), reverse=True)
