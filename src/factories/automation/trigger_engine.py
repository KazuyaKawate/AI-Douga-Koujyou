"""trigger_engine — evaluate rule-based triggers against current system state.

All evaluations are READ-ONLY. No data is written here.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent


def _read_json(rel: str) -> dict:
    p = ROOT / rel
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _result(fired: bool, reason: str, context: dict | None = None) -> dict:
    return {"fired": fired, "reason": reason, "context": context or {}}


# ── Trigger evaluators ────────────────────────────────────────────────────────

def _eval_status_changed(config: dict) -> dict:
    source = config.get("source", "")
    field  = config.get("field",  "status")
    value  = config.get("value",  "")
    if not source:
        return _result(False, "source未設定")

    data = _read_json(f"config/{source}")
    items: list[dict] = []
    for key in ("articles", "posts", "deals", "leads", "revenue", "expenses"):
        if key in data:
            items = data[key]
            break

    matched = [i for i in items if i.get(field) == value]
    if matched:
        return _result(
            True,
            f"{source}: {len(matched)} 件が {field}={value}",
            {"matched_items": matched[:3], "matched_count": len(matched)},
        )
    return _result(False, f"{source}: {field}={value} の項目なし")


def _eval_kpi_below_target(config: dict) -> dict:
    threshold = config.get("threshold_pct", 50)
    data      = _read_json("config/kpi_targets.json")
    targets   = data.get("targets", {})
    actuals   = data.get("actuals", {})
    if not targets:
        return _result(False, "KPIデータなし")

    below = []
    for key, target in targets.items():
        if not isinstance(target, (int, float)) or target == 0:
            continue
        actual = actuals.get(key, 0)
        pct    = round(actual / target * 100)
        if pct < threshold:
            below.append({"key": key, "actual": actual, "target": target, "pct": pct})
    if below:
        return _result(
            True,
            f"{len(below)} 件のKPIが目標の {threshold}% 未満",
            {"below_items": below},
        )
    return _result(False, f"全KPIが目標の {threshold}% 以上")


def _eval_new_item_created(config: dict) -> dict:
    source = config.get("source", "")
    today  = date.today().isoformat()
    if not source:
        return _result(False, "source未設定")

    data  = _read_json(f"config/{source}")
    items = next(
        (data[k] for k in ("articles", "posts", "deals", "leads", "revenue") if k in data),
        [],
    )
    today_items = [
        i for i in items
        if i.get("created_at", "")[:10] == today or i.get("entry_date", "")[:10] == today
    ]
    if today_items:
        return _result(
            True,
            f"今日 {len(today_items)} 件の新規アイテム",
            {"new_items": today_items[:3]},
        )
    return _result(False, "今日の新規アイテムなし")


def _eval_revenue_recorded(config: dict) -> dict:
    today = date.today().isoformat()[:7]  # YYYY-MM
    data  = _read_json("config/accounting_revenue.json")
    items = data.get("revenue", [])
    this_month = [i for i in items if i.get("entry_date", "")[:7] == today]
    if this_month:
        total = sum(i.get("amount", 0) for i in this_month)
        return _result(
            True,
            f"今月 {len(this_month)} 件 ¥{total:,} の売上",
            {"revenue_items": this_month[:3], "total": total},
        )
    return _result(False, "今月の売上データなし")


def _eval_warning_detected(config: dict) -> dict:
    min_w = config.get("min_warnings", 1)
    warnings: list[str] = []

    # Factory status warnings
    fs_data = _read_json("config/factory_status.json")
    fs      = fs_data.get("factories", fs_data)
    for name, info in fs.items():
        if isinstance(info, dict) and info.get("warning_count", 0) > 0:
            warnings.append(f"{name}: {info['warning_count']} 件の警告")

    # Accounting audit warnings
    try:
        from src.factories.accounting.audit_checker import check_audits
        from src.factories.analytics.analytics_collector import _read_json as _arj
        rev  = _read_json("config/accounting_revenue.json")
        exp  = _read_json("config/accounting_expenses.json")
        sub  = _read_json("config/accounting_subscriptions.json")
        aws  = check_audits(rev, exp, sub)
        for w in aws:
            warnings.append(f"会計監査: {w.get('message', '')}")
    except Exception:
        pass

    if len(warnings) >= min_w:
        return _result(
            True,
            f"{len(warnings)} 件の警告を検出",
            {"warnings": warnings[:5]},
        )
    return _result(False, f"警告なし (検出数: {len(warnings)}, 最小: {min_w})")


def _eval_manual_run(_config: dict) -> dict:
    return _result(True, "手動実行", {})


# ── Dispatcher ────────────────────────────────────────────────────────────────

_EVALUATORS = {
    "status_changed":   _eval_status_changed,
    "kpi_below_target": _eval_kpi_below_target,
    "new_item_created": _eval_new_item_created,
    "revenue_recorded": _eval_revenue_recorded,
    "warning_detected": _eval_warning_detected,
    "manual_run":       _eval_manual_run,
}


def evaluate_trigger(trigger_type: str, trigger_config: dict) -> dict:
    """Evaluate a trigger. Returns {fired, reason, context}. READ-ONLY."""
    evaluator = _EVALUATORS.get(trigger_type)
    if not evaluator:
        return _result(False, f"不明なトリガータイプ: {trigger_type}")
    try:
        return evaluator(trigger_config)
    except Exception as exc:
        return _result(False, f"評価エラー: {exc}")
