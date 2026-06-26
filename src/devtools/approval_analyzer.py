"""Approval Analyzer — main analysis pipeline for Claude Code approval prompts."""
import json
import uuid
from datetime import datetime
from pathlib import Path

from src.devtools.command_classifier import classify, get_dominant_risk, detect_tool_type, extract_file_paths
from src.devtools.risk_rules import RISK_LEVELS
from src.devtools.approval_templates import get_template, get_recommendation_text, DEFAULT_TEMPLATE

HISTORY_PATH = Path(__file__).parent.parent.parent / "config" / "approval_history.json"
MAX_HISTORY = 100


def analyze(raw_prompt: str) -> dict:
    """
    Analyze a Claude Code approval prompt.
    Returns a structured result dict.
    """
    if not raw_prompt.strip():
        return _empty_result()

    matches = classify(raw_prompt)
    risk_level_key = get_dominant_risk(matches)
    risk_info = RISK_LEVELS[risk_level_key]
    tool_type = detect_tool_type(raw_prompt)
    file_paths = extract_file_paths(raw_prompt)

    # Build explanation from matched templates
    primary_match = matches[0] if matches else None
    tmpl = get_template(primary_match["key"]) if primary_match else DEFAULT_TEMPLATE

    # Aggregate warnings from all matched patterns
    all_warnings = list(tmpl.get("warnings", []))
    for m in matches[1:4]:  # up to 3 additional matches
        extra_tmpl = get_template(m["key"])
        for w in extra_tmpl.get("warnings", []):
            if w not in all_warnings:
                all_warnings.append(w)

    # Next instruction: use the most dangerous match's instruction
    next_instruction = None
    for m in matches:
        t = get_template(m["key"])
        if t.get("next_instruction"):
            next_instruction = t["next_instruction"]
            break

    # Summary: 1-line natural Japanese
    if primary_match:
        summary = f"{primary_match['description']}の操作（{risk_info['icon']} {risk_info['label']}）"
    else:
        summary = f"不明な操作（内容を確認してください）"

    # What and why
    what = tmpl.get("what", DEFAULT_TEMPLATE["what"])
    why = _enrich_why(tmpl.get("why", DEFAULT_TEMPLATE["why"]), matches, file_paths)
    after = tmpl.get("after", DEFAULT_TEMPLATE["after"])

    recommendation = risk_info["recommendation"]

    result = {
        "id":                    f"approval_{uuid.uuid4().hex[:8]}",
        "timestamp":             datetime.now().isoformat(timespec="seconds"),
        "raw_prompt":            raw_prompt[:2000],
        "tool_type":             tool_type,
        "file_paths":            file_paths,
        "classified_commands":   matches,
        "risk_level":            risk_level_key,
        "risk_icon":             risk_info["icon"],
        "risk_label":            risk_info["label"],
        "risk_description":      risk_info["description"],
        "recommendation":        recommendation,
        "recommendation_label":  risk_info["rec_label"],
        "recommendation_text":   get_recommendation_text(recommendation),
        "summary":               summary,
        "what_it_does":          what,
        "why_needed":            why,
        "what_happens_after":    after,
        "warnings":              all_warnings,
        "next_instruction":      next_instruction,
    }

    _save_history(result)
    return result


def _enrich_why(base_why: str, matches: list[dict], file_paths: list[str]) -> str:
    """Append detected file paths to the why text."""
    if file_paths:
        paths_str = "、".join(file_paths[:5])
        return f"{base_why}（対象ファイル: {paths_str}）"
    return base_why


def _empty_result() -> dict:
    return {
        "id": "",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "raw_prompt": "",
        "tool_type": "unknown",
        "file_paths": [],
        "classified_commands": [],
        "risk_level": "safe",
        "risk_icon": "🟢",
        "risk_label": "安全",
        "risk_description": "入力が空です。",
        "recommendation": "yes",
        "recommendation_label": "✅ 承認してOK",
        "recommendation_text": "✅ 承認してOKです",
        "summary": "（入力なし）",
        "what_it_does": "",
        "why_needed": "",
        "what_happens_after": "",
        "warnings": [],
        "next_instruction": None,
    }


def _load_history() -> dict:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"history": [], "meta": {"version": "4.4.1", "created_at": "2026-06-27"}}


def _save_history(result: dict) -> None:
    data = _load_history()
    entry = {
        "id":               result["id"],
        "timestamp":        result["timestamp"],
        "raw_prompt":       result["raw_prompt"][:500],
        "risk_level":       result["risk_level"],
        "risk_icon":        result["risk_icon"],
        "recommendation":   result["recommendation"],
        "summary":          result["summary"],
        "warnings":         result.get("warnings", []),
    }
    data["history"].insert(0, entry)
    if len(data["history"]) > MAX_HISTORY:
        data["history"] = data["history"][:MAX_HISTORY]
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history(limit: int = 20) -> list[dict]:
    data = _load_history()
    return data.get("history", [])[:limit]


def get_latest_risk() -> dict | None:
    """Return the most recent history entry, or None if empty."""
    history = load_history(1)
    return history[0] if history else None


def clear_history() -> None:
    HISTORY_PATH.write_text(
        json.dumps({"history": [], "meta": {"version": "4.4.1"}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
