"""recommendation_engine — Generate strategic recommendations for AI CEO Core.

IMPORTANT: Recommendations only. Never executes actions.
Each recommendation includes: title, reason, expected_impact, confidence, related_factory, action
"""
from __future__ import annotations


def generate_recommendations(
    snap: dict,
    risks: list[dict],
    opportunities: list[dict],
    priorities: list[dict],
) -> list[dict]:
    recs: list[dict] = []

    kpi_rows = snap.get("kpi", {}).get("rows", [])
    finance  = snap.get("finance", {})
    month    = finance.get("month", {})
    month_rev  = month.get("revenue", 0)
    month_exp  = month.get("expense", 0)
    breakeven  = month.get("breakeven", 50000)
    task_stats = snap.get("tasks", {}).get("stats", {})
    note       = snap.get("note", {})
    sns        = snap.get("sns", {})
    auto_wf    = snap.get("automation", {}).get("workflows", {})
    ds         = snap.get("devstudio", {})

    # ── Revenue recovery ──────────────────────────────────────────────────────
    if month_exp > 0 and month_rev < month_exp:
        recs.append({
            "title": "収益回復を最優先にする",
            "reason": f"今月費用(¥{month_exp:,})が売上(¥{month_rev:,})を超過。赤字状態。",
            "expected_impact": "High",
            "confidence": 95,
            "related_factory": "会計監査工場 / 営業工場",
            "action": "営業工場でアクティブリードへの即時フォローを実施。note/SNS投稿でオーガニックリードを獲得してください。",
        })

    if 0 < month_rev < breakeven:
        remaining = breakeven - month_rev
        recs.append({
            "title": f"損益分岐点まで ¥{remaining:,} の売上が必要",
            "reason": f"今月売上 ¥{month_rev:,} / 損益分岐点 ¥{breakeven:,}。",
            "expected_impact": "High",
            "confidence": 90,
            "related_factory": "営業工場",
            "action": "商談中案件の早期クローズを優先。月末前に確定できる案件を特定してください。",
        })

    # ── Task completion ───────────────────────────────────────────────────────
    pct = task_stats.get("pct", 100)
    if pct < 50 and task_stats.get("total", 0) > 2:
        recs.append({
            "title": "今日のタスク完了率を上げる",
            "reason": f"現在の完了率 {pct}%。高優先度タスクが積み残されています。",
            "expected_impact": "Medium",
            "confidence": 80,
            "related_factory": "Mission Control",
            "action": "Mission ControlでTop3優先タスクを確認して集中着手してください。",
        })

    # ── Content factory activation ────────────────────────────────────────────
    if note.get("draft", 0) > 0:
        recs.append({
            "title": f"note下書き {note['draft']} 件を公開する",
            "reason": "下書き記事が公開待ち状態。KPI達成とリーチ拡大の機会。",
            "expected_impact": "Medium",
            "confidence": 85,
            "related_factory": "note投稿工場",
            "action": "note投稿工場で下書きを確認しSEOスコアが最も高い記事から公開してください。",
        })

    if sns.get("total", 0) == 0:
        recs.append({
            "title": "SNS投稿を開始する",
            "reason": "SNS投稿工場に投稿が一件もありません。オーディエンスとの接点がゼロ。",
            "expected_impact": "Medium",
            "confidence": 75,
            "related_factory": "SNS投稿工場",
            "action": "SNS投稿工場でX/Threads向けの投稿を1件作成してください。noteの記事を転用するのが効率的です。",
        })

    # ── KPI-specific recommendations ─────────────────────────────────────────
    for row in kpi_rows:
        if not row.get("is_actual"):
            continue
        if row["pct"] == 0 and row["target"] > 0:
            recs.append({
                "title": f"{row['label']}を今日中に達成する",
                "reason": f"実績ゼロ (目標: {row['target']:,} {row['unit']})。",
                "expected_impact": "Medium",
                "confidence": 70,
                "related_factory": "Mission Control",
                "action": f"今日中に{row['label']}の実績を最低1件記録してください。",
            })

    # ── Automation ────────────────────────────────────────────────────────────
    if auto_wf.get("total", 0) > 0 and auto_wf.get("enabled", 0) == 0:
        recs.append({
            "title": "自動化ワークフローを有効化する",
            "reason": f"{auto_wf.get('total', 0)} ワークフローが定義済みだが全て無効。",
            "expected_impact": "Medium",
            "confidence": 65,
            "related_factory": "自動化工場",
            "action": "自動化工場でドライランモードでワークフローを有効化し動作を確認してください。",
        })

    # ── Roadmap decisions ─────────────────────────────────────────────────────
    if ds.get("open_decisions", 0) > 0:
        recs.append({
            "title": f"オープン決定事項 {ds.get('open_decisions', 0)} 件を解決する",
            "reason": "未決定事項が積み残されると開発速度が低下します。",
            "expected_impact": "Medium",
            "confidence": 80,
            "related_factory": "Development Studio",
            "action": "Development StudioのDecision Logを開いて高影響決定から順に解決してください。",
        })

    # ── Opportunities-based ───────────────────────────────────────────────────
    for opp in opportunities[:3]:
        if opp.get("potential") == "high":
            recs.append({
                "title": f"機会を活用: {opp['title']}",
                "reason": opp.get("detail", ""),
                "expected_impact": "High",
                "confidence": 70,
                "related_factory": opp.get("factory", ""),
                "action": f"{opp.get('factory', '')} を開いて対応を開始してください。",
            })

    # ── Risk-based ────────────────────────────────────────────────────────────
    for risk in risks:
        if risk.get("severity") == "high" and len(recs) < 10:
            exists = any(risk["title"][:20] in r["title"] for r in recs)
            if not exists:
                recs.append({
                    "title": f"リスク対応: {risk['title']}",
                    "reason": risk.get("detail", ""),
                    "expected_impact": "High",
                    "confidence": 85,
                    "related_factory": risk.get("factory", ""),
                    "action": f"{risk.get('factory', '')} でリスク状況を確認・対処してください。",
                })

    return recs[:10]
