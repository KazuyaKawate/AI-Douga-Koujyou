"""Command Classifier — detect command patterns in Claude Code approval prompts."""
import re
from src.devtools.risk_rules import COMMAND_PATTERNS, RISK_ORDER, highest_risk


def classify(raw_prompt: str) -> list[dict]:
    """Return list of matched command patterns, ordered by risk (highest first)."""
    matched: list[dict] = []
    seen_keys: set[str] = set()

    for risk_level, key, pattern, description in COMMAND_PATTERNS:
        if re.search(pattern, raw_prompt, re.IGNORECASE | re.DOTALL):
            if key not in seen_keys:
                seen_keys.add(key)
                matched.append({
                    "risk": risk_level,
                    "key": key,
                    "pattern": pattern,
                    "description": description,
                })

    # Sort: most dangerous first
    risk_order_map = {r: i for i, r in enumerate(RISK_ORDER)}
    matched.sort(key=lambda m: risk_order_map.get(m["risk"], 99))
    return matched


def get_dominant_risk(matches: list[dict]) -> str:
    """Return the highest risk level across all matches."""
    if not matches:
        return "safe"
    return highest_risk([m["risk"] for m in matches])


def detect_tool_type(raw_prompt: str) -> str:
    """Try to detect if this is a Bash command, file write, file edit, or read."""
    lower = raw_prompt.lower()
    if any(kw in lower for kw in ("bash", "powershell", "command:", "コマンド:")):
        return "bash"
    if any(kw in lower for kw in ("write", "new file", "ファイルを作成", "書き込み")):
        return "write"
    if any(kw in lower for kw in ("edit", "modify", "old_string", "変更", "修正")):
        return "edit"
    if any(kw in lower for kw in ("read", "読み取り", "読み込み")):
        return "read"
    if any(kw in lower for kw in ("glob", "grep", "search", "検索")):
        return "search"
    return "unknown"


def extract_file_paths(raw_prompt: str) -> list[str]:
    """Extract likely file paths from the prompt text."""
    pattern = r'[a-zA-Z_\-\\/\.]+\.(py|json|md|txt|bat|ps1|csv|yaml|yml|env)'
    return list(set(re.findall(pattern, raw_prompt, re.IGNORECASE)))


def is_read_only(raw_prompt: str) -> bool:
    """Return True if the prompt appears to be purely read-only."""
    matches = classify(raw_prompt)
    if not matches:
        return True
    levels = [m["risk"] for m in matches]
    return all(l == "safe" for l in levels)
