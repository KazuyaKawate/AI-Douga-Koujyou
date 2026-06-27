"""factory_analyzer — analyze factory health and activity across all factories."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
_FS_PATH = ROOT / "config" / "factory_status.json"

HEALTH_ICONS = {"ok": "✅", "degraded": "🟡", "failed": "🔴"}
STATUS_ICONS = {"active": "🟢", "idle": "⚪", "warning": "🟠", "stopped": "🔴"}


def _load_factory_status() -> dict:
    if _FS_PATH.exists():
        try:
            data = json.loads(_FS_PATH.read_text(encoding="utf-8"))
            return data.get("factories", data)
        except Exception:
            pass
    return {}


def analyze_factories() -> dict:
    """Return factory health + activity summary."""
    try:
        from src.core.factory_registry import FactoryRegistry
        health_list = FactoryRegistry.check_all_health()
    except Exception:
        health_list = []

    fs = _load_factory_status()
    results = []
    for h in health_list:
        name = h["factory"]
        info = fs.get(name, {})
        results.append({
            "name":            name,
            "health":          h["health"],
            "health_icon":     HEALTH_ICONS.get(h["health"], "⚪"),
            "status":          info.get("status", "idle"),
            "status_icon":     STATUS_ICONS.get(info.get("status", "idle"), "⚪"),
            "active_items":    info.get("active_items", 0),
            "completed_today": info.get("completed_today", 0),
            "warning_count":   info.get("warning_count", 0),
            "next_action":     info.get("next_action", "—"),
        })

    total   = len(results)
    healthy = sum(1 for r in results if r["health"] == "ok")
    return {
        "factories":      results,
        "total":          total,
        "healthy":        healthy,
        "health_pct":     round(healthy / total * 100) if total else 0,
        "total_warnings": sum(r["warning_count"] for r in results),
        "total_active":   sum(r["active_items"]   for r in results),
        "total_completed":sum(r["completed_today"] for r in results),
    }


def get_factory_insights(analysis: dict) -> list[str]:
    """Return rule-based factory insight strings."""
    insights: list[str] = []
    if not analysis["factories"]:
        return ["📊 工場データがありません"]
    pct = analysis["health_pct"]
    if pct == 100:
        insights.append(f"✅ 全 {analysis['total']} 工場が正常稼働中")
    else:
        degraded = [f["name"] for f in analysis["factories"] if f["health"] != "ok"]
        insights.append(f"⚠️ {len(degraded)} 工場が設定不足: {', '.join(degraded)}")
    if analysis["total_warnings"] > 0:
        insights.append(f"🔔 合計 {analysis['total_warnings']} 件の警告があります")
    active = analysis["total_active"]
    if active > 0:
        insights.append(f"🏭 現在 {active} 件のアイテムが稼働中")
    if analysis["total_completed"] > 0:
        insights.append(f"✅ 今日の完了数: {analysis['total_completed']} 件")
    return insights
