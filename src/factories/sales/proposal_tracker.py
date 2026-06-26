"""Proposal tracker — create and track proposals through response status lifecycle."""
import json
import uuid
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sales_deals.json"
PROPOSAL_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sales_proposals.json"

RESPONSE_STATUSES = ["draft", "sent", "replied", "accepted", "declined"]

RESPONSE_LABELS = {
    "draft":    "下書き",
    "sent":     "送付済",
    "replied":  "返信あり",
    "accepted": "承諾",
    "declined": "辞退",
}

RESPONSE_ICONS = {
    "draft":    "📝",
    "sent":     "📨",
    "replied":  "💬",
    "accepted": "✅",
    "declined": "❌",
}


def load_proposals() -> dict:
    if PROPOSAL_PATH.exists():
        try:
            return json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"proposals": [], "meta": {"version": "4.5"}}


def save_proposals(data: dict) -> None:
    PROPOSAL_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_proposal(
    title: str,
    amount: int = 0,
    lead_id: str = "",
    deal_id: str = "",
    sent_date: str = "",
    memo: str = "",
) -> dict:
    data = load_proposals()
    now = datetime.now().isoformat(timespec="seconds")
    proposal = {
        "proposal_id":     "prop_" + uuid.uuid4().hex[:8],
        "lead_id":         lead_id,
        "deal_id":         deal_id,
        "title":           title,
        "amount":          amount,
        "sent_date":       sent_date,
        "response_status": "draft",
        "memo":            memo,
        "created_at":      now,
        "updated_at":      now,
    }
    data["proposals"].append(proposal)
    save_proposals(data)
    return proposal


def update_proposal_status(proposal_id: str, new_status: str, **kwargs) -> tuple[bool, str, dict | None]:
    if new_status not in RESPONSE_STATUSES:
        return False, f"不明なステータス: {new_status}", None
    data = load_proposals()
    for prop in data["proposals"]:
        if prop["proposal_id"] == proposal_id:
            prop["response_status"] = new_status
            for k, v in kwargs.items():
                prop[k] = v
            prop["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_proposals(data)
            label = RESPONSE_LABELS.get(new_status, new_status)
            return True, f"ステータスを「{label}」に更新しました", prop
    return False, f"提案 {proposal_id} が見つかりません", None


def delete_proposal(proposal_id: str) -> bool:
    data = load_proposals()
    before = len(data["proposals"])
    data["proposals"] = [p for p in data["proposals"] if p["proposal_id"] != proposal_id]
    if len(data["proposals"]) < before:
        save_proposals(data)
        return True
    return False


def get_proposal_summary(data: dict) -> dict:
    proposals = data.get("proposals", [])
    return {
        "total":    len(proposals),
        "draft":    sum(1 for p in proposals if p.get("response_status") == "draft"),
        "sent":     sum(1 for p in proposals if p.get("response_status") == "sent"),
        "accepted": sum(1 for p in proposals if p.get("response_status") == "accepted"),
        "declined": sum(1 for p in proposals if p.get("response_status") == "declined"),
        "total_amount": sum(p.get("amount", 0) for p in proposals),
        "accepted_amount": sum(p.get("amount", 0) for p in proposals if p.get("response_status") == "accepted"),
    }
