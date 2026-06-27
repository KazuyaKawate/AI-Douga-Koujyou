"""risk_engine — Identify OS risks for AI CEO Core.

Categories: revenue, project_delay, factory_degradation, roadmap, health
Each risk has: category, severity (high/medium/low), title, detail, factory
"""
from __future__ import annotations
from datetime import date

TODAY = date.today().isoformat()
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


def identify_risks(snap: dict) -> list[dict]:
    risks: list[dict] = []

    # ── Revenue risks ─────────────────────────────────────────────────────────
    finance = snap.get("finance", {})
    month   = finance.get("month", {})
    month_rev  = month.get("revenue", 0)
    month_exp  = month.get("expense", 0)
    breakeven  = month.get("breakeven", 50000)

    if month_exp > 0 and month_rev < month_exp:
        risks.append({
            "category": "revenue",
            "severity": "high",
            "title": "今月費用が売上を超過",
            "detail": f"売上 ¥{month_rev:,} < 費用 ¥{month_exp:,}。赤字運営中。",
            "factory": "会計監査工場",
            "icon": "🔴",
        })
    elif month_rev < breakeven * 0.5 and breakeven > 0:
        risks.append({
            "category": "revenue",
            "severity": "high",
            "title": "損益分岐点の50%未達",
            "detail": f"今月売上 ¥{month_rev:,} / 損益分岐点 ¥{breakeven:,}。",
            "factory": "会計監査工場",
            "icon": "🔴",
        })
    elif month_rev < breakeven:
        risks.append({
            "category": "revenue",
            "severity": "medium",
            "title": "損益分岐点未達",
            "detail": f"今月売上 ¥{month_rev:,} / 目標 ¥{breakeven:,}。",
            "factory": "会計監査工場",
            "icon": "⚠️",
        })

    acc = snap.get("accounting", {})
    roi_data = acc.get("roi", {})
    if roi_data.get("roi", 0) < 0:
        risks.append({
            "category": "revenue",
            "severity": "high",
            "title": f"ROIがマイナス ({roi_data.get('roi', 0)}%)",
            "detail": "投資対効果が負。費用削減またはコンバージョン改善が必要。",
            "factory": "会計監査工場",
            "icon": "🔴",
        })

    audit = acc.get("audit", {})
    if audit.get("errors", 0) > 0:
        risks.append({
            "category": "revenue",
            "severity": "high",
            "title": f"会計監査エラー {audit['errors']} 件",
            "detail": "会計工場で監査エラーが検出されています。",
            "factory": "会計監査工場",
            "icon": "🔴",
        })

    # ── Sales risks ───────────────────────────────────────────────────────────
    sales = snap.get("sales", {})
    followups = sales.get("followups", {})
    if followups.get("overdue", 0) > 0:
        risks.append({
            "category": "revenue",
            "severity": "medium",
            "title": f"営業フォロー期限超過 {followups['overdue']} 件",
            "detail": "期限超過のフォローアップが放置されています。",
            "factory": "営業工場",
            "icon": "⚠️",
        })

    # ── KPI risks ─────────────────────────────────────────────────────────────
    kpi_rows = snap.get("kpi", {}).get("rows", [])
    for row in kpi_rows:
        if not row.get("is_actual"):
            continue
        if row["pct"] == 0 and row["target"] > 0:
            risks.append({
                "category": "kpi",
                "severity": "medium",
                "title": f"KPI未着手: {row['label']}",
                "detail": f"実績ゼロ (目標 {row['target']:,} {row['unit']})。",
                "factory": "Mission Control",
                "icon": "⚠️",
            })

    # ── Task completion risks ─────────────────────────────────────────────────
    task_stats = snap.get("tasks", {}).get("stats", {})
    if task_stats.get("pct", 100) < 20 and task_stats.get("total", 0) > 0:
        risks.append({
            "category": "kpi",
            "severity": "medium",
            "title": f"今日のタスク完了率が低い ({task_stats.get('pct', 0)}%)",
            "detail": f"完了 {task_stats.get('done', 0)}/{task_stats.get('total', 0)} タスク。",
            "factory": "Mission Control",
            "icon": "⚠️",
        })

    # ── Factory degradation ───────────────────────────────────────────────────
    registry = snap.get("registry", {})
    fac_reg  = registry.get("factories", {})
    if fac_reg.get("total", 0) > 0:
        degraded = fac_reg.get("total", 0) - fac_reg.get("healthy", 0)
        if degraded > 0:
            risks.append({
                "category": "factory_degradation",
                "severity": "medium",
                "title": f"工場健全性低下: {degraded} 工場",
                "detail": f"FactoryRegistry: {fac_reg.get('healthy', 0)}/{fac_reg.get('total', 0)} 正常。",
                "factory": "Core Architecture",
                "icon": "⚠️",
            })

    anl_fac = snap.get("analytics", {}).get("factories", {})
    if anl_fac.get("health_pct", 100) < 60:
        risks.append({
            "category": "factory_degradation",
            "severity": "high",
            "title": f"工場健全性 {anl_fac.get('health_pct', 0)}% — 重大低下",
            "detail": "複数の工場が低パフォーマンス状態です。",
            "factory": "アナリティクス工場",
            "icon": "🔴",
        })

    # ── Roadmap / incomplete risks ────────────────────────────────────────────
    ds = snap.get("devstudio", {})
    if ds.get("blocked_decisions", 0) > 0:
        risks.append({
            "category": "roadmap",
            "severity": "medium",
            "title": f"高影響の未決定事項 {ds['blocked_decisions']} 件",
            "detail": "高影響のオープン決定がロードマップをブロックしている可能性。",
            "factory": "Development Studio",
            "icon": "⚠️",
        })

    try:
        from src.devstudio.roadmap_manager import get_all_items
        blocked = [r for r in get_all_items() if r.get("status") == "blocked"]
        if blocked:
            risks.append({
                "category": "roadmap",
                "severity": "medium",
                "title": f"ロードマップ ブロック中 {len(blocked)} 件",
                "detail": ", ".join(r.get("title", "") for r in blocked[:3]),
                "factory": "Development Studio",
                "icon": "⚠️",
            })
        overdue = [
            r for r in get_all_items()
            if r.get("planned_date", "9999") < TODAY and r.get("status") not in ("completed", "archived")
        ]
        if overdue:
            risks.append({
                "category": "project_delay",
                "severity": "medium",
                "title": f"ロードマップ期限超過 {len(overdue)} 件",
                "detail": ", ".join(r.get("title", "") for r in overdue[:3]),
                "factory": "Development Studio",
                "icon": "⚠️",
            })
    except Exception:
        pass

    # ── SNS risks ────────────────────────────────────────────────────────────
    sns = snap.get("sns", {})
    if sns.get("total", 0) == 0:
        risks.append({
            "category": "kpi",
            "severity": "low",
            "title": "SNS投稿がゼロ",
            "detail": "SNS工場に投稿がありません。コンテンツ発信を開始してください。",
            "factory": "SNS投稿工場",
            "icon": "🟡",
        })

    risks.sort(key=lambda r: (SEV_ORDER.get(r["severity"], 9), r["category"]))
    return risks
