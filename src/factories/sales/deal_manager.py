"""Deal manager — commercial pipeline with stage transitions and KPI side-effects."""
import json
import uuid
from datetime import date, datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sales_deals.json"

STAGES = ["new", "contacted", "meeting", "proposal_sent", "negotiation", "contracted", "lost"]

STAGE_LABELS = {
    "new":           "新規",
    "contacted":     "連絡済",
    "meeting":       "商談中",
    "proposal_sent": "提案送付",
    "negotiation":   "交渉中",
    "contracted":    "成約",
    "lost":          "失注",
}

STAGE_ICONS = {
    "new":           "🆕",
    "contacted":     "📨",
    "meeting":       "🤝",
    "proposal_sent": "📋",
    "negotiation":   "💬",
    "contracted":    "🏆",
    "lost":          "❌",
}

STAGE_PROBABILITY = {
    "new":           10,
    "contacted":     20,
    "meeting":       35,
    "proposal_sent": 50,
    "negotiation":   70,
    "contracted":    100,
    "lost":          0,
}

ACTIVE_STAGES = {"new", "contacted", "meeting", "proposal_sent", "negotiation"}


def load_deals() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"deals": [], "meta": {"version": "4.5"}}


def save_deals(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_deal(
    title: str,
    lead_id: str = "",
    stage: str = "new",
    amount: int = 0,
    probability: int | None = None,
    expected_close_date: str = "",
    memo: str = "",
) -> dict:
    data = load_deals()
    now = datetime.now().isoformat(timespec="seconds")
    deal_id = "deal_" + uuid.uuid4().hex[:8]
    if probability is None:
        probability = STAGE_PROBABILITY.get(stage, 10)
    deal = {
        "deal_id":             deal_id,
        "lead_id":             lead_id,
        "title":               title,
        "stage":               stage,
        "amount":              amount,
        "probability":         probability,
        "expected_close_date": expected_close_date,
        "status":              "active",
        "memo":                memo,
        "created_at":          now,
        "updated_at":          now,
        "contracted_at":       None,
    }
    data["deals"].append(deal)
    save_deals(data)
    return deal


def update_deal(deal_id: str, **kwargs) -> dict | None:
    data = load_deals()
    for deal in data["deals"]:
        if deal["deal_id"] == deal_id:
            for k, v in kwargs.items():
                deal[k] = v
            deal["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_deals(data)
            return deal
    return None


def transition_stage(deal_id: str, new_stage: str) -> tuple[bool, str, dict | None]:
    if new_stage not in STAGES:
        return False, f"不明なステージ: {new_stage}", None
    data = load_deals()
    for deal in data["deals"]:
        if deal["deal_id"] == deal_id:
            old_stage = deal["stage"]
            if old_stage == new_stage:
                return False, "同じステージです", deal
            deal["stage"] = new_stage
            deal["probability"] = STAGE_PROBABILITY.get(new_stage, deal["probability"])
            deal["updated_at"] = datetime.now().isoformat(timespec="seconds")
            if new_stage == "contracted":
                deal["status"] = "won"
                deal["contracted_at"] = deal["updated_at"]
                _on_contract(deal)
            elif new_stage == "lost":
                deal["status"] = "lost"
            elif new_stage in ACTIVE_STAGES:
                deal["status"] = "active"
            save_deals(data)
            label = STAGE_LABELS.get(new_stage, new_stage)
            return True, f"ステージを「{label}」に更新しました", deal
    return False, f"商談 {deal_id} が見つかりません", None


def _on_contract(deal: dict) -> None:
    try:
        from src.hq.factory_status import load_factory_status, save_factory_status
        fd = load_factory_status()
        if "営業工場" in fd:
            fd["営業工場"]["completed_today"] = fd["営業工場"].get("completed_today", 0) + 1
            fd["営業工場"]["status"] = "active"
            fd["営業工場"]["next_action"] = f"成約: {deal.get('title', '')} ¥{deal.get('amount', 0):,}"
        save_factory_status(fd)
    except Exception:
        pass


def delete_deal(deal_id: str) -> bool:
    data = load_deals()
    before = len(data["deals"])
    data["deals"] = [d for d in data["deals"] if d["deal_id"] != deal_id]
    if len(data["deals"]) < before:
        save_deals(data)
        return True
    return False


def get_factory_summary(data: dict) -> dict:
    deals = data.get("deals", [])
    today_str = date.today().isoformat()
    active = [d for d in deals if d.get("status") == "active"]
    contracted = [d for d in deals if d.get("status") == "won"]
    lost = [d for d in deals if d.get("status") == "lost"]
    pipeline_total = sum(d.get("amount", 0) for d in active)
    weighted = sum(d.get("amount", 0) * d.get("probability", 0) / 100 for d in active)
    contracted_total = sum(d.get("amount", 0) for d in contracted)
    contracted_today = sum(
        1 for d in contracted
        if (d.get("contracted_at") or "")[:10] == today_str
    )
    return {
        "total":            len(deals),
        "active":           len(active),
        "contracted":       len(contracted),
        "lost":             len(lost),
        "pipeline_total":   int(pipeline_total),
        "weighted_forecast": int(weighted),
        "contracted_total": int(contracted_total),
        "contracted_today": contracted_today,
    }
