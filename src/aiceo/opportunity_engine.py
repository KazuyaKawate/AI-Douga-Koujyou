"""opportunity_engine — Identify strategic opportunities for AI CEO Core.

Categories: roi, unused_factory, automation, content
Each opportunity has: category, potential (high/medium/low), title, detail, factory
"""
from __future__ import annotations

POT_ORDER = {"high": 0, "medium": 1, "low": 2}


def identify_opportunities(snap: dict) -> list[dict]:
    opps: list[dict] = []

    # ── Highest ROI opportunities ─────────────────────────────────────────────
    sales = snap.get("sales", {})
    leads = sales.get("leads", {})
    deals = sales.get("deals", {})
    forecast = sales.get("forecast", {})

    if leads.get("total", 0) > 0 and deals.get("active", 0) == 0:
        opps.append({
            "category": "roi",
            "potential": "high",
            "title": "リードが商談に転換されていない",
            "detail": f"リード {leads.get('total', 0)} 件あるが商談中ゼロ。積極的にアプローチを。",
            "factory": "営業工場",
            "icon": "💡",
        })

    expected = forecast.get("expected_monthly", 0)
    if expected > 0:
        opps.append({
            "category": "roi",
            "potential": "high",
            "title": f"今月売上予測 ¥{expected:,}",
            "detail": "営業パイプラインに売上ポテンシャルあり。商談をクローズしてください。",
            "factory": "営業工場",
            "icon": "💰",
        })

    acc = snap.get("accounting", {})
    roi_data = acc.get("roi", {})
    if roi_data.get("roi", 0) > 50:
        opps.append({
            "category": "roi",
            "potential": "high",
            "title": f"ROI {roi_data.get('roi', 0)}% — 高投資効率",
            "detail": "高ROIを維持中。現在の収益モデルを拡張するチャンス。",
            "factory": "会計監査工場",
            "icon": "📈",
        })

    # ── Unused / underutilized factories ──────────────────────────────────────
    note = snap.get("note", {})
    if note.get("draft", 0) > 0 and note.get("published", 0) == 0:
        opps.append({
            "category": "unused_factory",
            "potential": "medium",
            "title": f"note下書き {note['draft']} 件が未公開",
            "detail": "記事を公開してKPI達成とオーガニックリーチを獲得しましょう。",
            "factory": "note投稿工場",
            "icon": "📝",
        })
    elif note.get("total", 0) == 0:
        opps.append({
            "category": "unused_factory",
            "potential": "medium",
            "title": "note投稿工場が未活用",
            "detail": "note記事を作成してコンテンツマーケティングを始めてください。",
            "factory": "note投稿工場",
            "icon": "📝",
        })

    sns = snap.get("sns", {})
    if sns.get("scheduled", 0) > 0:
        opps.append({
            "category": "content",
            "potential": "medium",
            "title": f"SNSスケジュール済み {sns['scheduled']} 件",
            "detail": "スケジュール済み投稿があります。予定通り公開されているか確認してください。",
            "factory": "SNS投稿工場",
            "icon": "📱",
        })
    elif sns.get("total", 0) == 0:
        opps.append({
            "category": "unused_factory",
            "potential": "medium",
            "title": "SNS投稿工場が未活用",
            "detail": "SNS投稿を作成してオーディエンスとのエンゲージメントを高めましょう。",
            "factory": "SNS投稿工場",
            "icon": "📱",
        })

    # ── Automation candidates ─────────────────────────────────────────────────
    auto = snap.get("automation", {})
    wf   = auto.get("workflows", {})
    runs = auto.get("runs", {})

    if wf.get("total", 0) > 0 and wf.get("enabled", 0) == 0:
        opps.append({
            "category": "automation",
            "potential": "medium",
            "title": "自動化ワークフローが全て無効",
            "detail": f"{wf.get('total', 0)} ワークフローが定義済みだが有効化されていない。",
            "factory": "自動化工場",
            "icon": "⚙️",
        })
    elif wf.get("total", 0) == 0:
        opps.append({
            "category": "automation",
            "potential": "low",
            "title": "自動化ワークフロー未定義",
            "detail": "ルールベース自動化でタスクを自動化できます。",
            "factory": "自動化工場",
            "icon": "⚙️",
        })
    elif wf.get("enabled", 0) > 0 and runs.get("total_runs", 0) == 0:
        opps.append({
            "category": "automation",
            "potential": "medium",
            "title": "有効化ワークフローが未実行",
            "detail": f"{wf.get('enabled', 0)} ワークフローが有効だが実行履歴なし。トライガー条件を確認してください。",
            "factory": "自動化工場",
            "icon": "⚙️",
        })

    # ── Content opportunities ─────────────────────────────────────────────────
    kpi_rows = snap.get("kpi", {}).get("rows", [])
    video_row = next((r for r in kpi_rows if r.get("key") == "video_count"), None)
    if video_row and video_row.get("actual", 0) == 0 and video_row.get("target", 0) > 0:
        opps.append({
            "category": "content",
            "potential": "high",
            "title": "今日の動画制作ゼロ",
            "detail": f"動画目標 {video_row['target']} 本未達。AI動画工場で制作を開始してください。",
            "factory": "AI動画工場",
            "icon": "🎬",
        })

    registry = snap.get("registry", {})
    proj_reg = registry.get("projects", {})
    if proj_reg.get("active_projects", 0) == 0:
        opps.append({
            "category": "unused_factory",
            "potential": "medium",
            "title": "稼働中プロジェクトなし",
            "detail": "Project Managerでプロジェクトを作成して工場を活用しましょう。",
            "factory": "Project Manager",
            "icon": "📁",
        })

    opps.sort(key=lambda o: POT_ORDER.get(o["potential"], 9))
    return opps
