"""executive_report.py — Generate and export Markdown executive report for AI CEO Core."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
REPORT_DIR = ROOT / "reports" / "aiceo"


def _ensure_dir() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR


def generate_report(
    snap: dict,
    health: dict,
    ceo_brief: str,
    priorities: list[dict],
    risks: list[dict],
    opportunities: list[dict],
    recommendations: list[dict],
    kpi_analysis: dict,
) -> str:
    now   = datetime.now()
    today = now.strftime("%Y-%m-%d")
    ts    = now.strftime("%Y-%m-%d %H:%M")

    lines: list[str] = []
    lines.append(f"# AI CEO Executive Report — {today}")
    lines.append(f"\n_Generated: {ts} | OS: Creator Factory OS v5.0-beta_\n")

    # Brief
    lines.append("## CEO Daily Brief\n")
    lines.append(ceo_brief + "\n")

    # Overall Health
    lines.append(f"## Overall Health: {health['icon']} {health['label']} ({health['score']}%)\n")
    lines.append(f"- High Risk Items: {health['high_risks']}\n")

    # KPI
    lines.append("## KPI Summary\n")
    lines.append(f"- Average Achievement: **{kpi_analysis.get('avg_pct', 0)}%**\n")
    for row in kpi_analysis.get("summary", []):
        lines.append(f"- {row['icon']} {row['label']}: {row['actual']:,} / {row['target']:,} {row['unit']} ({row['pct']}%)")
    lines.append("")

    # Finance
    month = snap.get("finance", {}).get("month", {})
    lines.append("## Revenue Summary\n")
    lines.append(f"- 今月売上: ¥{month.get('revenue', 0):,}")
    lines.append(f"- 今月費用: ¥{month.get('expense', 0):,}")
    profit = month.get("revenue", 0) - month.get("expense", 0)
    lines.append(f"- 今月利益: ¥{profit:,}")
    lines.append(f"- 損益分岐点: ¥{month.get('breakeven', 0):,}\n")

    # Priorities
    lines.append("## Top Priorities\n")
    for i, p in enumerate(priorities, 1):
        over = " ⏰OVERDUE" if p.get("overdue") else ""
        lines.append(f"{i}. {p['icon']} [{p['source'].upper()}] **{p['title']}** "
                     f"(score: {p['score']} | {p['status']}){over}")
    lines.append("")

    # Risks
    lines.append("## Top Risks\n")
    if risks:
        for r in risks:
            lines.append(f"- {r['icon']} **[{r['severity'].upper()}]** {r['title']} — _{r['detail']}_")
    else:
        lines.append("- No significant risks identified.\n")
    lines.append("")

    # Opportunities
    lines.append("## Top Opportunities\n")
    if opportunities:
        for o in opportunities:
            lines.append(f"- {o['icon']} **[{o['potential'].upper()}]** {o['title']} — _{o['detail']}_")
    else:
        lines.append("- No opportunities identified.\n")
    lines.append("")

    # Recommendations
    lines.append("## Recommended Actions\n")
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"### {i}. {rec['title']}")
        lines.append(f"- **Reason:** {rec['reason']}")
        lines.append(f"- **Expected Impact:** {rec['expected_impact']} | **Confidence:** {rec['confidence']}%")
        lines.append(f"- **Related Factory:** {rec['related_factory']}")
        lines.append(f"- **Action:** {rec['action']}\n")

    lines.append("---")
    lines.append(f"_Creator Factory OS v5.0-beta — AI CEO Executive Report — {ts}_")

    return "\n".join(lines)


def export_report(content: str) -> Path:
    _ensure_dir()
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"{ts}_executive_report.md"
    path.write_text(content, encoding="utf-8")
    return path


def get_report_history() -> list[dict]:
    _ensure_dir()
    files = sorted(REPORT_DIR.glob("*_executive_report.md"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            "name": f.name,
            "path": str(f),
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "content": f.read_text(encoding="utf-8") if f.stat().st_size < 200_000 else "",
        }
        for f in files[:20]
    ]
