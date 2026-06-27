"""automation_rules — trigger/action constants and built-in workflow templates."""
from __future__ import annotations

# ── Trigger type constants ─────────────────────────────────────────────────────

TRIGGER_STATUS_CHANGED   = "status_changed"
TRIGGER_KPI_BELOW_TARGET = "kpi_below_target"
TRIGGER_NEW_ITEM_CREATED = "new_item_created"
TRIGGER_REVENUE_RECORDED = "revenue_recorded"
TRIGGER_WARNING_DETECTED = "warning_detected"
TRIGGER_MANUAL_RUN       = "manual_run"

ALL_TRIGGER_TYPES = (
    TRIGGER_STATUS_CHANGED,
    TRIGGER_KPI_BELOW_TARGET,
    TRIGGER_NEW_ITEM_CREATED,
    TRIGGER_REVENUE_RECORDED,
    TRIGGER_WARNING_DETECTED,
    TRIGGER_MANUAL_RUN,
)

TRIGGER_LABELS: dict[str, str] = {
    TRIGGER_STATUS_CHANGED:   "ステータス変更",
    TRIGGER_KPI_BELOW_TARGET: "KPI未達",
    TRIGGER_NEW_ITEM_CREATED: "新規アイテム",
    TRIGGER_REVENUE_RECORDED: "売上計上",
    TRIGGER_WARNING_DETECTED: "警告検出",
    TRIGGER_MANUAL_RUN:       "手動実行",
}

TRIGGER_ICONS: dict[str, str] = {
    TRIGGER_STATUS_CHANGED:   "🔄",
    TRIGGER_KPI_BELOW_TARGET: "📉",
    TRIGGER_NEW_ITEM_CREATED: "✨",
    TRIGGER_REVENUE_RECORDED: "💰",
    TRIGGER_WARNING_DETECTED: "⚠️",
    TRIGGER_MANUAL_RUN:       "▶️",
}

# ── Action type constants ──────────────────────────────────────────────────────

ACTION_CREATE_TASK            = "create_task"
ACTION_CREATE_SNS_DRAFT       = "create_sns_draft"
ACTION_CREATE_SALES_LEAD      = "create_sales_lead_candidate"
ACTION_CREATE_REVENUE_DRAFT   = "create_accounting_revenue_draft"
ACTION_CREATE_REPORT          = "create_report"
ACTION_UPDATE_FACTORY_STATUS  = "update_factory_status"

ALL_ACTION_TYPES = (
    ACTION_CREATE_TASK,
    ACTION_CREATE_SNS_DRAFT,
    ACTION_CREATE_SALES_LEAD,
    ACTION_CREATE_REVENUE_DRAFT,
    ACTION_CREATE_REPORT,
    ACTION_UPDATE_FACTORY_STATUS,
)

ACTION_LABELS: dict[str, str] = {
    ACTION_CREATE_TASK:           "タスク作成",
    ACTION_CREATE_SNS_DRAFT:      "SNS下書き作成",
    ACTION_CREATE_SALES_LEAD:     "見込み客候補追加",
    ACTION_CREATE_REVENUE_DRAFT:  "売上下書き作成",
    ACTION_CREATE_REPORT:         "レポート生成",
    ACTION_UPDATE_FACTORY_STATUS: "工場ステータス更新",
}

ACTION_ICONS: dict[str, str] = {
    ACTION_CREATE_TASK:           "✅",
    ACTION_CREATE_SNS_DRAFT:      "📱",
    ACTION_CREATE_SALES_LEAD:     "💼",
    ACTION_CREATE_REVENUE_DRAFT:  "💰",
    ACTION_CREATE_REPORT:         "📝",
    ACTION_UPDATE_FACTORY_STATUS: "🏭",
}

# ── Built-in workflow templates ────────────────────────────────────────────────

WORKFLOW_TEMPLATES: list[dict] = [
    {
        "workflow_id":    "wf_note_to_sns",
        "name":           "note公開 → SNS下書き生成",
        "description":    "note記事が公開されたら、SNS投稿の下書きを自動生成します。",
        "trigger_type":   TRIGGER_STATUS_CHANGED,
        "trigger_config": {"source": "note_articles.json", "field": "status", "value": "published"},
        "action_type":    ACTION_CREATE_SNS_DRAFT,
        "action_config":  {"platform": "X", "template": "note_article", "prefix": "📝 新記事を公開しました:"},
        "enabled":        True,
        "run_count":      0,
        "last_run":       "",
        "created_at":     "2026-06-27",
    },
    {
        "workflow_id":    "wf_sns_to_sales",
        "name":           "SNS公開 → 見込み客候補追加",
        "description":    "SNS投稿が公開されたら、反応した人を見込み客候補としてCRMに下書き追加します。",
        "trigger_type":   TRIGGER_STATUS_CHANGED,
        "trigger_config": {"source": "sns_posts.json", "field": "status", "value": "published"},
        "action_type":    ACTION_CREATE_SALES_LEAD,
        "action_config":  {"source": "SNS", "rank": "C", "memo": "SNS経由の見込み客候補（自動生成）"},
        "enabled":        False,
        "run_count":      0,
        "last_run":       "",
        "created_at":     "2026-06-27",
    },
    {
        "workflow_id":    "wf_deal_to_accounting",
        "name":           "商談成約 → 売上下書き作成",
        "description":    "商談が成約したら、会計工場に売上下書きエントリーを自動作成します。",
        "trigger_type":   TRIGGER_STATUS_CHANGED,
        "trigger_config": {"source": "sales_deals.json", "field": "stage", "value": "contracted"},
        "action_type":    ACTION_CREATE_REVENUE_DRAFT,
        "action_config":  {"source": "sales", "status": "pending", "memo": "商談成約（自動生成）"},
        "enabled":        True,
        "run_count":      0,
        "last_run":       "",
        "created_at":     "2026-06-27",
    },
    {
        "workflow_id":    "wf_warning_to_task",
        "name":           "警告検出 → Mission Controlタスク追加",
        "description":    "工場警告や監査アラートが検出されたら、Mission Controlにタスクを追加します。",
        "trigger_type":   TRIGGER_WARNING_DETECTED,
        "trigger_config": {"min_warnings": 1},
        "action_type":    ACTION_CREATE_TASK,
        "action_config":  {"category": "会計監査工場", "priority": "high",
                           "title_prefix": "⚠️ 要対応:"},
        "enabled":        True,
        "run_count":      0,
        "last_run":       "",
        "created_at":     "2026-06-27",
    },
    {
        "workflow_id":    "wf_kpi_to_suggestion",
        "name":           "KPI未達 → CEOサジェスト生成",
        "description":    "KPI達成率が50%未満の場合、改善アクションのサジェストレポートを生成します。",
        "trigger_type":   TRIGGER_KPI_BELOW_TARGET,
        "trigger_config": {"threshold_pct": 50},
        "action_type":    ACTION_CREATE_REPORT,
        "action_config":  {"report_type": "kpi_suggestion"},
        "enabled":        True,
        "run_count":      0,
        "last_run":       "",
        "created_at":     "2026-06-27",
    },
]
