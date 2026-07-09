from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


AREA_TARGETS: dict[str, dict[str, Any]] = {
    "note": {
        "engine": "content_factory",
        "tokens": ("note", "記事", "有料note"),
        "files": ["src/content_factory/note_builder.py", "src/revenue_engine/note_manager.py"],
        "steps": ["note読者ニーズを整理", "記事構成とCTA案を作成", "収益導線の差分をDryRunで確認"],
        "expected_income": 12000,
        "expected_time": 3,
        "difficulty": 2,
        "channel": "note",
    },
    "threads": {
        "engine": "revenue",
        "tokens": ("threads", "実投稿", "投稿", "初クリック"),
        "files": ["src/business_engine/threads_automation.py", "src/revenue_engine/threads_manager.py"],
        "steps": ["投稿仮説を整理", "Threads投稿案と計測導線を作成", "Diffとテスト結果を確認"],
        "expected_income": 6000,
        "expected_time": 1,
        "difficulty": 1,
        "channel": "Threads",
    },
    "website": {
        "engine": "growth",
        "tokens": ("公式サイト", "official", "site", "seo", "cta", "lp"),
        "files": ["src/official_site/site_manager.py", "src/official_site/website_engine.py", "pages/34_Official_Site.py"],
        "steps": ["SEO/CTA改善点を抽出", "公式サイト改善案を作成", "表示と導線への影響を確認"],
        "expected_income": 20000,
        "expected_time": 5,
        "difficulty": 3,
        "channel": "Website",
    },
    "seo": {
        "engine": "growth",
        "tokens": ("seo", "検索", "流入"),
        "files": ["src/growth_engine/seo_manager.py", "src/official_site/website_engine.py"],
        "steps": ["検索流入の改善仮説を整理", "タイトル/導線/内部リンク案を作成", "SEO影響範囲を確認"],
        "expected_income": 15000,
        "expected_time": 3,
        "difficulty": 2,
    },
    "affiliate": {
        "engine": "revenue",
        "tokens": ("affiliate", "Affiliate", "アフィリエイト", "クリック", "成約"),
        "files": ["src/revenue_engine/affiliate_manager.py", "src/official_site/website_engine.py"],
        "steps": ["成約導線を整理", "クリック率改善案を作成", "収益導線の差分を確認"],
        "expected_income": 18000,
        "expected_time": 2,
        "difficulty": 2,
    },
    "commander": {
        "engine": "coding_engine",
        "tokens": ("commander", "司令塔", "dryrun", "approve", "execute"),
        "files": ["src/commander/console_page.py", "src/commander/queue.py", "src/commander/worker.py"],
        "steps": ["Commander要件を分解", "安全ガードとUI差分を作成", "Commander系テストで確認"],
        "expected_income": 8000,
        "expected_time": 4,
        "difficulty": 3,
    },
    "business": {
        "engine": "business",
        "tokens": ("business", "事業", "収益", "kpi"),
        "files": ["src/business_engine/manager.py", "src/revenue_engine/revenue_manager.py"],
        "steps": ["収益KPIを整理", "最短収益タスクへ分解", "実行順をROIで決定"],
        "expected_income": 10000,
        "expected_time": 2,
        "difficulty": 2,
    },
    "development": {
        "engine": "coding_engine",
        "tokens": ("development", "開発", "改善", "実装"),
        "files": ["src/commander/console_page.py", "src/commander/planner.py"],
        "steps": ["実装対象を限定", "DryRun可能な差分を作成", "Commander系テストを確認"],
        "expected_income": 4000,
        "expected_time": 4,
        "difficulty": 3,
    },
    "maintenance": {
        "engine": "coding_engine",
        "tokens": ("maintenance", "保守", "修正", "バグ"),
        "files": ["src/commander/worker.py", "tests/test_commander_console_api.py"],
        "steps": ["問題を再現", "最小修正を作成", "回帰テストを確認"],
        "expected_income": 1000,
        "expected_time": 2,
        "difficulty": 2,
    },
    "coding": {
        "engine": "coding_engine",
        "tokens": ("git差分", "test", "review", "coding commander", "コードレビュー"),
        "files": ["src/coding_engine/coding_manager.py", "src/commander/worker.py"],
        "steps": ["Git差分を確認", "TestをDryRunで実行", "Review結果を保存"],
        "expected_income": 3000,
        "expected_time": 2,
        "difficulty": 2,
    },
    "release": {
        "engine": "coding_engine",
        "tokens": ("release", "リリース", "rollback", "approve release"),
        "files": ["src/commander/queue.py", "src/commander/console_page.py"],
        "steps": ["Release DryRun", "Review", "Approve待ち", "Release手順生成", "Rollback手順生成"],
        "expected_income": 2000,
        "expected_time": 2,
        "difficulty": 3,
    },
}


class CommanderPlanner:
    def build_plan(self, instruction: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        text = instruction.lower()
        areas = [name for name, rule in AREA_TARGETS.items() if any(token.lower() in text for token in rule["tokens"])]
        if not areas:
            areas = ["note"]
        target_files = list(dict.fromkeys([*metadata.get("target_files", []), *self._target_files(areas)]))
        business_task = self.build_business_task(instruction, areas, metadata)
        steps = []
        for area in areas:
            steps.extend(AREA_TARGETS[area]["steps"])
        return {
            "plan_id": f"plan-{uuid4().hex[:8]}",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "instruction": instruction,
            "priority_scope": areas,
            "engine": AREA_TARGETS[areas[0]]["engine"],
            "steps": [{"index": index + 1, "title": step, "status": "planned"} for index, step in enumerate(dict.fromkeys(steps))],
            "impacted_files": target_files,
            "business_task": business_task,
            "roi": business_task["roi"],
            "priority_score": business_task["priority_score"],
            "risk": self.risk(areas, business_task),
            "implementation_order": list(range(1, len(steps) + 1)),
            "automation_plan": self.automation_plan(areas, business_task),
            "ai_employee": self.employee(areas),
            "approval_required": True,
            "dry_run_first": True,
            "callback_targets": ["business", "revenue", "growth", "content", "publish", "coding_engine"],
            "content_commander": self.content_channels(areas),
            "coding_commander": self.coding_workflow(areas),
            "release_approval": self.release_workflow(areas),
        }

    def build_business_task(self, instruction: str, areas: list[str], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        rules = [AREA_TARGETS[area] for area in areas]
        expected_income = int(metadata.get("expected_income") or sum(rule["expected_income"] for rule in rules))
        expected_time = float(metadata.get("expected_time") or max(1, sum(rule["expected_time"] for rule in rules)))
        difficulty = int(metadata.get("difficulty") or max(rule["difficulty"] for rule in rules))
        deadline = str(metadata.get("deadline") or "today")
        urgency = {"today": 30, "this_week": 15}.get(deadline, 5)
        roi = round(expected_income / expected_time, 2)
        priority_score = round((roi / 100) + urgency - (difficulty * 5), 2)
        return {
            "task_id": f"bt-{uuid4().hex[:8]}",
            "title": instruction[:80],
            "task_type": areas[0],
            "categories": areas,
            "expected_revenue": expected_income,
            "expected_income": expected_income,
            "expected_time": expected_time,
            "deadline": deadline,
            "roi": roi,
            "difficulty": difficulty,
            "priority_score": priority_score,
            "status": "waiting",
        }

    @staticmethod
    def content_channels(areas: list[str]) -> dict[str, Any]:
        channels = [AREA_TARGETS[area].get("channel") for area in areas if AREA_TARGETS[area].get("channel")]
        return {"enabled": bool(channels), "channels": channels}

    @staticmethod
    def coding_workflow(areas: list[str]) -> dict[str, Any]:
        enabled = any(area in {"coding", "development", "maintenance", "commander"} for area in areas)
        return {"enabled": enabled, "steps": ["git_diff", "test", "review", "release_candidate"] if enabled else []}

    @staticmethod
    def release_workflow(areas: list[str]) -> dict[str, Any]:
        enabled = "release" in areas
        return {"enabled": enabled, "steps": ["dry_run", "review", "approve", "release", "rollback"] if enabled else [], "requires_approval": True}

    @staticmethod
    def risk(areas: list[str], task: dict[str, Any]) -> str:
        if "release" in areas:
            return "high"
        if int(task.get("difficulty", 0)) >= 3:
            return "medium"
        return "low"

    @staticmethod
    def automation_plan(areas: list[str], task: dict[str, Any]) -> dict[str, Any]:
        return {
            "cron": "0 8 * * *" if task.get("deadline") == "today" else "0 9 * * 1",
            "workflow": [f"{area}_dry_run" for area in areas],
            "auto_execute": False,
            "requires_approval": True,
        }

    @staticmethod
    def employee(areas: list[str]) -> str:
        if "note" in areas:
            return "Writer"
        if "website" in areas or "seo" in areas:
            return "SEO"
        if "threads" in areas or "affiliate" in areas:
            return "Marketing"
        if "development" in areas or "coding" in areas or "commander" in areas:
            return "Developer"
        if "maintenance" in areas or "release" in areas:
            return "Reviewer"
        return "Business"

    @staticmethod
    def _target_files(areas: list[str]) -> list[str]:
        files: list[str] = []
        for area in areas:
            files.extend(AREA_TARGETS[area]["files"])
        return files
