"""FactoryRegistry — auto-register and query all Creator Factory OS factories."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from src.core.factory_interfaces import FactoryCatalogEntry

ROOT = Path(__file__).parent.parent.parent

# ── Static catalog ─────────────────────────────────────────────────────────────
# Each entry describes a factory without importing its module.
# Modules are imported lazily only when health checks run.

FACTORY_CATALOG: dict[str, FactoryCatalogEntry] = {
    "AI動画工場": {
        "name":         "AI動画工場",
        "icon":         "🎬",
        "version":      "4.1",
        "module_path":  "src.core.ai_pipeline",
        "page":         "pages/16_AI_Studio.py",
        "config_files": ["config/settings.json"],
        "dependencies": [],
        "description":  "AI動画制作パイプライン（スクリプト/字幕/組立/エクスポート）",
    },
    "note投稿工場": {
        "name":         "note投稿工場",
        "icon":         "📝",
        "version":      "4.3",
        "module_path":  "src.factories.note",
        "page":         "pages/18_Note_Factory.py",
        "config_files": ["config/note_articles.json"],
        "dependencies": [],
        "description":  "note記事管理・スコアリング・収益・コンテンツ転用",
    },
    "SNS投稿工場": {
        "name":         "SNS投稿工場",
        "icon":         "📱",
        "version":      "4.4",
        "module_path":  "src.factories.sns",
        "page":         "pages/19_SNS_Factory.py",
        "config_files": ["config/sns_posts.json", "config/sns_platforms.json"],
        "dependencies": ["note投稿工場"],
        "description":  "7プラットフォーム対応SNS投稿管理・スケジュール・分析",
    },
    "承認アシスタント": {
        "name":         "承認アシスタント",
        "icon":         "🔍",
        "version":      "4.4.1",
        "module_path":  "src.devtools",
        "page":         "pages/20_Approval_Assistant.py",
        "config_files": ["config/approval_rules.json", "config/approval_history.json"],
        "dependencies": [],
        "description":  "Claude Code承認プロンプト分類・リスク評価（4段階）",
    },
    "営業工場": {
        "name":         "営業工場",
        "icon":         "💼",
        "version":      "4.5",
        "module_path":  "src.factories.sales",
        "page":         "pages/21_Sales_Factory.py",
        "config_files": [
            "config/sales_leads.json",
            "config/sales_deals.json",
            "config/sales_followups.json",
        ],
        "dependencies": [],
        "description":  "CRM・リード管理・商談パイプライン・売上予測",
    },
    "会計監査工場": {
        "name":         "会計監査工場",
        "icon":         "💰",
        "version":      "4.6",
        "module_path":  "src.factories.accounting",
        "page":         "pages/22_Accounting_Factory.py",
        "config_files": [
            "config/accounting_revenue.json",
            "config/accounting_expenses.json",
            "config/accounting_subscriptions.json",
        ],
        "dependencies": ["営業工場"],
        "description":  "収支管理・ROI・サブスク・監査・月次レポート",
    },
}


class FactoryRegistry:
    """Query interface for the factory catalog."""

    # ── Catalog access ─────────────────────────────────────────────────────────

    @staticmethod
    def get_all() -> list[FactoryCatalogEntry]:
        return list(FACTORY_CATALOG.values())

    @staticmethod
    def get(name: str) -> FactoryCatalogEntry | None:
        return FACTORY_CATALOG.get(name)

    @staticmethod
    def get_names() -> list[str]:
        return list(FACTORY_CATALOG.keys())

    @staticmethod
    def get_by_version(version_prefix: str) -> list[FactoryCatalogEntry]:
        return [f for f in FACTORY_CATALOG.values() if f["version"].startswith(version_prefix)]

    # ── Health check ───────────────────────────────────────────────────────────

    @staticmethod
    def check_health(name: str) -> dict:
        """Lightweight health check: verify config files and page exist."""
        entry = FACTORY_CATALOG.get(name)
        if not entry:
            return {"factory": name, "health": "failed", "reason": "not in catalog"}

        checks: list[dict] = []
        all_ok = True

        page_ok = (ROOT / entry["page"]).exists()
        checks.append({"name": "page_exists", "passed": page_ok, "file": entry["page"]})
        if not page_ok:
            all_ok = False

        for cfg in entry["config_files"]:
            cfg_ok = (ROOT / cfg).exists()
            checks.append({"name": "config_exists", "passed": cfg_ok, "file": cfg})
            if not cfg_ok:
                all_ok = False

        health = "ok" if all_ok else "degraded"
        return {
            "factory": name,
            "health":  health,
            "checks":  checks,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }

    @staticmethod
    def check_all_health() -> list[dict]:
        return [FactoryRegistry.check_health(n) for n in FACTORY_CATALOG]

    # ── Summary ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_summary() -> dict:
        all_health = FactoryRegistry.check_all_health()
        ok_count      = sum(1 for h in all_health if h["health"] == "ok")
        degraded_count = sum(1 for h in all_health if h["health"] == "degraded")
        failed_count   = sum(1 for h in all_health if h["health"] == "failed")
        return {
            "total":    len(FACTORY_CATALOG),
            "healthy":  ok_count,
            "degraded": degraded_count,
            "failed":   failed_count,
            "factories": all_health,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    @staticmethod
    def get_factory_names_for_project(project_factories: list[str]) -> list[FactoryCatalogEntry]:
        """Return catalog entries matching a list of factory names."""
        return [FACTORY_CATALOG[n] for n in project_factories if n in FACTORY_CATALOG]
