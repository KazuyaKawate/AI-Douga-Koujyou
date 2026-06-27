"""trend_reporter — rule-based insights, report generation, and snapshot persistence."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

ROOT         = Path(__file__).parent.parent.parent.parent
REPORTS_DIR  = ROOT / "reports" / "analytics"
SNAPSHOTS_PATH = ROOT / "config" / "analytics_snapshots.json"
MAX_SNAPSHOTS = 30


# ── Snapshot persistence ──────────────────────────────────────────────────────

def load_snapshots() -> dict:
    if SNAPSHOTS_PATH.exists():
        try:
            return json.loads(SNAPSHOTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"snapshots": [], "meta": {"version": "4.7", "limit": MAX_SNAPSHOTS}}


def save_snapshot(snapshot: dict) -> None:
    data = load_snapshots()
    record = {
        "snapshot_id": "snap_" + uuid.uuid4().hex[:8],
        "timestamp":   snapshot.get("timestamp", datetime.now().isoformat(timespec="seconds")),
        "summary": {
            "factory_registry": snapshot.get("factory_registry", {}),
            "project_count":    len(snapshot.get("projects", [])),
        },
    }
    data["snapshots"].append(record)
    if len(data["snapshots"]) > MAX_SNAPSHOTS:
        data["snapshots"] = data["snapshots"][-MAX_SNAPSHOTS:]
    SNAPSHOTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_snapshots(limit: int = 10) -> list[dict]:
    data = load_snapshots()
    snaps = data.get("snapshots", [])
    return list(reversed(snaps[-limit:]))


# ── Insight synthesis ─────────────────────────────────────────────────────────

def synthesize_insights(
    kpi_ins: list[str],
    factory_ins: list[str],
    project_ins: list[str],
    roi_ins: list[str],
) -> list[str]:
    """Merge and prioritize all insights. Errors first, then warnings, then info."""
    errors   = [i for g in (kpi_ins, factory_ins, project_ins, roi_ins) for i in g if i.startswith("🔴")]
    warnings = [i for g in (kpi_ins, factory_ins, project_ins, roi_ins) for i in g if i.startswith("⚠️")]
    checks   = [i for g in (kpi_ins, factory_ins, project_ins, roi_ins) for i in g if i.startswith("✅")]
    info     = [i for g in (kpi_ins, factory_ins, project_ins, roi_ins) for i in g
                if not any(i.startswith(p) for p in ("🔴", "⚠️", "✅"))]
    return errors + warnings + checks + info


# ── Report generation ─────────────────────────────────────────────────────────

def generate_analytics_report(
    snapshot: dict,
    kpi_analysis: dict,
    factory_analysis: dict,
    project_analysis: dict,
    roi_analysis: dict,
    all_insights: list[str],
) -> str:
    ts = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    lines: list[str] = [
        f"# Analytics Report — {datetime.now().strftime('%Y-%m-%d')}",
        f"生成日時: {ts}  |  Creator Factory OS v4.7",
        "",
        "---",
        "",
        "## システムサマリー",
        "",
        f"| 項目 | 値 |",
        f"|------|---|",
        f"| 工場数 | {factory_analysis['total']} 工場 |",
        f"| 正常工場 | {factory_analysis['healthy']}/{factory_analysis['total']} ({factory_analysis['health_pct']}%) |",
        f"| KPI平均達成率 | {kpi_analysis['avg_pct']}% |",
        f"| 稼働プロジェクト | {project_analysis['active']}/{project_analysis['total']} |",
        f"| 今月売上 | ¥{roi_analysis['total_revenue']:,} |",
        f"| 今月利益 | ¥{roi_analysis['net_profit']:,} |",
        f"| ROI | {roi_analysis['roi']}% |",
        "",
        "---",
        "",
        "## インサイト",
        "",
    ]
    for ins in all_insights:
        lines.append(f"- {ins}")
    lines += ["", "---", "", "## KPI分析", ""]
    if kpi_analysis["rows"]:
        lines.append("| 指標 | 目標 | 実績 | 達成率 |")
        lines.append("|------|------|------|--------|")
        for r in kpi_analysis["rows"]:
            unit = r["unit"]
            lines.append(
                f"| {r['label']} | {r['target']:,}{unit} | {r['actual']:,}{unit} | {r['pct']}% |"
            )
    else:
        lines.append("KPIデータなし")
    lines += ["", "---", "", "## 工場分析", ""]
    if factory_analysis["factories"]:
        lines.append("| 工場 | 健全性 | 状態 | 稼働中 | 完了(今日) | 警告 |")
        lines.append("|------|--------|------|--------|------------|------|")
        for f in factory_analysis["factories"]:
            lines.append(
                f"| {f['name']} | {f['health_icon']} {f['health']} | {f['status']} "
                f"| {f['active_items']} | {f['completed_today']} | {f['warning_count']} |"
            )
    lines += ["", "---", "", "## プロジェクト分析", ""]
    if project_analysis["summaries"]:
        lines.append("| プロジェクト | 状態 | 進捗 | 工場数 | 売上 |")
        lines.append("|-------------|------|------|--------|------|")
        for p in project_analysis["summaries"]:
            lines.append(
                f"| {p['name']} | {p['status_icon']} {p['status_label']} "
                f"| {p['progress']:.0f}% | {p['factory_count']} | ¥{p['revenue']:,} |"
            )
    lines += ["", "---", "", "## ROI分析", ""]
    lines += [
        f"- 今月売上: ¥{roi_analysis['total_revenue']:,}",
        f"- 今月経費: ¥{roi_analysis['month_expense']:,}",
        f"- サブスク費用: ¥{roi_analysis['sub_cost']:,}/月 ({roi_analysis['active_subs']}サービス)",
        f"- 合計支出: ¥{roi_analysis['total_expense']:,}",
        f"- 今月利益: ¥{roi_analysis['net_profit']:,}",
        f"- ROI: {roi_analysis['roi']}%",
    ]
    if roi_analysis["revenue_by_source"]:
        lines += ["", "**収入源別:**"]
        for src, amt in sorted(roi_analysis["revenue_by_source"].items(), key=lambda x: -x[1]):
            lines.append(f"- {src}: ¥{amt:,}")
    lines += ["", "---", "", "## 推奨アクション", ""]
    errors   = [i for i in all_insights if i.startswith("🔴")]
    warnings = [i for i in all_insights if i.startswith("⚠️")]
    actions  = errors + warnings
    if actions:
        for i, a in enumerate(actions, 1):
            lines.append(f"{i}. {a}")
    else:
        lines.append("特に優先対応が必要な項目はありません。")
    lines += ["", "---", f"*Creator Factory OS Analytics Factory v4.7*"]
    return "\n".join(lines)


def export_analytics_report(content: str, date_str: str = "") -> Path:
    """Write report to reports/analytics/YYYY-MM-DD_analytics_report.md."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{date_str or datetime.now().strftime('%Y-%m-%d')}_analytics_report.md"
    path = REPORTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path


def list_reports() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("*_analytics_report.md"), reverse=True)
