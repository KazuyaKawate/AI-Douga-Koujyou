"""REVENUE-9 local owner decision workflow; no external execution."""
from __future__ import annotations

import json
import os
import shutil
import time
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

FIELD_LABELS = {
    "service_name": "Service Name", "target_customer": "Target Customer", "deliverables": "Deliverables",
    "exclusions": "Exclusions", "delivery_days": "Delivery Days", "revision_count": "Revision Count",
    "starter_price": "Starter Price", "standard_price": "Standard Price", "premium_price": "Premium Price",
    "tax_treatment": "Tax Treatment", "payment_timing": "Payment Timing", "payment_method": "Payment Method",
    "cancellation_policy": "Cancellation Policy", "refund_policy": "Refund Policy",
}
PRICE_FIELDS = ("starter_price", "standard_price", "premium_price")
INTEGER_FIELDS = ("delivery_days", "revision_count", *PRICE_FIELDS)
CONFIRMATION = "OWNER APPROVED"
SAFETY = {"local_first": True, "dry_run": True, "approval_required": True, "execute_allowed": False,
          "production_actions_enabled": False, "external_request_sent": False, "review_required": True,
          "activation_status": "BLOCKED", "production_status": "NO-GO", "verified_revenue_jpy": 0}
DEFAULT_STORE = Path("data/revenue9_owner_decisions.json")
DEFAULT_HISTORY = Path("data/revenue9_decision_history.jsonl")
LOCK_TIMEOUT_SECONDS = 5.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_workspace() -> dict[str, Any]:
    return {"version": 1, "safety": deepcopy(SAFETY), "fields": {
        key: {"value": "", "status": "UNDECIDED", "notes": "", "updated_at": "",
              "approved_at": "", "evidence_reference": ""} for key in FIELD_LABELS}}


class OwnerDecisionStore:
    def __init__(self, store_path: Path = DEFAULT_STORE, history_path: Path = DEFAULT_HISTORY):
        self.store_path, self.history_path = Path(store_path), Path(history_path)
        self.lock_path = self.store_path.with_suffix(self.store_path.suffix + ".lock")

    @contextmanager
    def _locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline, descriptor = time.monotonic() + LOCK_TIMEOUT_SECONDS, None
        while descriptor is None:
            try:
                descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(descriptor, f"pid={os.getpid()}\n".encode())
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("REVENUE-9 repository is locked by another local process")
                time.sleep(0.05)
        try:
            yield
        finally:
            os.close(descriptor)
            self.lock_path.unlink(missing_ok=True)

    def _load_unlocked(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return empty_workspace()
        payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        if payload.get("safety") != SAFETY or set(payload.get("fields", {})) != set(FIELD_LABELS):
            raise ValueError("Invalid or unsafe REVENUE-9 local workspace")
        return payload

    def load(self) -> dict[str, Any]:
        with self._locked():
            return self._load_unlocked()

    @staticmethod
    def _backup(path: Path) -> None:
        if path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store_path.with_suffix(self.store_path.suffix + ".tmp")
        self._backup(self.store_path)
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.store_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _append_many(self, records: list[dict[str, Any]]) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self._backup(self.history_path)
        with self.history_path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _record(field: str, previous: Any, new: Any, action: str, reviewer: str) -> dict[str, Any]:
        return {"timestamp": utc_now(), "field": field, "previous_value": previous,
                "new_value": new, "action": action, "reviewer": reviewer}

    def save_draft(self, values: dict[str, dict[str, Any]], reviewer: str = "OWNER") -> dict[str, Any]:
        with self._locked():
            current, now, records = self._load_unlocked(), utc_now(), []
            for key in FIELD_LABELS:
                incoming, old = values.get(key, {}), current["fields"][key]
                new = {**old, "value": incoming.get("value", ""), "notes": incoming.get("notes", ""),
                       "evidence_reference": incoming.get("evidence_reference", ""), "status": "DRAFT",
                       "updated_at": now, "approved_at": ""}
                if old != new:
                    records.append(self._record(key, old, new, "SAVE_DRAFT", reviewer))
                current["fields"][key] = new
            if records:
                self._append_many(records)
            self._atomic_write(current)
            return current

    def transition(self, action: str, reviewer: str, confirmation: str = "") -> dict[str, Any]:
        target = {"SUBMIT_FOR_REVIEW": "REVIEW_REQUIRED", "REJECT": "REJECTED",
                  "RESET_DRAFT": "UNDECIDED", "APPROVE": "APPROVED"}.get(action)
        if not target:
            raise ValueError("Unsupported action")
        with self._locked():
            current, now, records = self._load_unlocked(), utc_now(), []
            if action in {"SUBMIT_FOR_REVIEW", "APPROVE"} and validate_workspace(current):
                raise ValueError("Validation errors must be resolved")
            if action == "APPROVE" and confirmation != CONFIRMATION:
                raise ValueError(f"Approval requires exact confirmation: {CONFIRMATION}")
            for key, old in list(current["fields"].items()):
                new = empty_workspace()["fields"][key] if action == "RESET_DRAFT" else deepcopy(old)
                if action != "RESET_DRAFT":
                    new.update(status=target, updated_at=now, approved_at=now if target == "APPROVED" else "")
                records.append(self._record(key, old, new, action, reviewer))
                current["fields"][key] = new
            self._append_many(records)
            self._atomic_write(current)
            return current


def _integer(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def validate_workspace(workspace: dict[str, Any]) -> list[str]:
    """Check completeness and format only, never business quality."""
    fields, errors = workspace["fields"], []
    for key, label in FIELD_LABELS.items():
        if not str(fields[key].get("value", "")).strip():
            errors.append(f"{label}: required")
    for key in INTEGER_FIELDS:
        value = _integer(fields[key].get("value"))
        if value is None:
            errors.append(f"{FIELD_LABELS[key]}: whole number required")
        elif value < 0 or (key == "delivery_days" and value < 1):
            errors.append(f"{FIELD_LABELS[key]}: invalid range")
    prices = [_integer(fields[key].get("value")) for key in PRICE_FIELDS]
    if all(value is not None and value >= 0 for value in prices) and not prices[0] <= prices[1] <= prices[2]:
        errors.append("Package hierarchy: Starter <= Standard <= Premium required")
    return list(dict.fromkeys(errors))


def summarize(workspace: dict[str, Any]) -> dict[str, Any]:
    fields = workspace["fields"]
    drafted = sum(bool(str(row["value"]).strip()) for row in fields.values())
    approved = sum(row["status"] == "APPROVED" for row in fields.values())
    priority = next((FIELD_LABELS[key] for key, row in fields.items() if row["status"] != "APPROVED"), "None")
    missing = [FIELD_LABELS[key] for key, row in fields.items() if not str(row["evidence_reference"]).strip()]
    return {"drafted": drafted, "approved": approved, "total": len(fields), "remaining": len(fields) - approved,
            "highest_priority": priority, "missing_evidence": missing, "validation_errors": validate_workspace(workspace)}


def render_owner_decision_workspace() -> None:
    store = OwnerDecisionStore()
    workspace = store.load()
    st.subheader("REVENUE-9 Owner Decision Workspace")
    st.caption("Local First / explicit save only / no autosave / Review Required")
    with st.form("revenue9_owner_decisions", clear_on_submit=False):
        values = {}
        for key, label in FIELD_LABELS.items():
            row = workspace["fields"][key]
            values[key] = {
                "value": st.text_input(label, value=str(row["value"]), key=f"r9v_{key}"),
                "notes": st.text_area(f"{label} Notes", value=row["notes"], key=f"r9n_{key}"),
                "evidence_reference": st.text_input(f"{label} Evidence Reference", value=row["evidence_reference"], key=f"r9e_{key}"),
            }
        reviewer = st.text_input("Reviewer", value="OWNER")
        confirmation = st.text_input(f'Approval confirmation (type "{CONFIRMATION}")')
        buttons = st.columns(5)
        pressed = [buttons[0].form_submit_button("Save Draft"), buttons[1].form_submit_button("Submit for Review"),
                   buttons[2].form_submit_button("Approve"), buttons[3].form_submit_button("Reject"),
                   buttons[4].form_submit_button("Reset Draft")]
    try:
        if pressed[0]:
            store.save_draft(values, reviewer); st.success("Draft saved locally."); st.rerun()
        for active, action in zip(pressed[1:], ("SUBMIT_FOR_REVIEW", "APPROVE", "REJECT", "RESET_DRAFT")):
            if active:
                store.transition(action, reviewer, confirmation); st.success(f"{action} recorded locally."); st.rerun()
    except ValueError as exc:
        st.error(str(exc))
    st.dataframe([{"Field": FIELD_LABELS[key], **row} for key, row in workspace["fields"].items()], hide_index=True, use_container_width=True)


def render_business_home(workspace: dict[str, Any] | None = None) -> None:
    summary = summarize(workspace or OwnerDecisionStore().load())
    st.subheader("REVENUE-9 Owner Decision Progress")
    for column, (label, value) in zip(st.columns(4), (("Draft Completion", f'{summary["drafted"]}/{summary["total"]}'),
        ("Approved Completion", f'{summary["approved"]}/{summary["total"]}'), ("Remaining Decisions", summary["remaining"]),
        ("Highest Priority Decision", summary["highest_priority"]))): column.metric(label, value)
    render_owner_decision_workspace()


def render_commander(workspace: dict[str, Any] | None = None) -> None:
    summary = summarize(workspace or OwnerDecisionStore().load())
    st.subheader("REVENUE-9 Commander / Display Only")
    st.write(f'**Next Owner Decision:** {summary["highest_priority"]}')
    st.write(f'**Validation Errors:** {len(summary["validation_errors"])}')
    st.write(f'**Missing Evidence:** {len(summary["missing_evidence"])}')


def render_executive(workspace: dict[str, Any] | None = None) -> None:
    summary = summarize(workspace or OwnerDecisionStore().load())
    st.subheader("REVENUE-9 Executive")
    for column, (label, value) in zip(st.columns(4), (("Draft Readiness", f'{summary["drafted"]}/{summary["total"]}'),
        ("Approval Progress", f'{summary["approved"]}/{summary["total"]}'), ("Activation Status", "BLOCKED"),
        ("Production", "NO-GO"))): column.metric(label, value)
