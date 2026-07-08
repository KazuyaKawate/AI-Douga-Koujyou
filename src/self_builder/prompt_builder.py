from __future__ import annotations

from typing import Any


PLAN_RULES = {
    "Free Plan": {
        "targets": "対象ファイルを3つ以内に限定",
        "forbidden": "大規模変更、危険操作、UI全体変更は禁止",
        "commands": "pytest 該当テストのみ",
        "report": "変更ファイル、変更内容、確認結果のみ",
    },
    "Pro Plan": {
        "targets": "対象機能に関係する pages/ と src/ のみ",
        "forbidden": "既存の本番処理、認証情報、無関係なリファクタは禁止",
        "commands": "pytest -q",
        "report": "変更ファイル、追加機能、確認結果、残課題",
    },
    "Release Plan": {
        "targets": "Releaseに必要な設定、確認、公開導線のみ",
        "forbidden": "記事生成ロジック、Business Engine本体、Threads本番処理の変更は禁止",
        "commands": "pytest -q / streamlit run app.py",
        "report": "不足設定、チェック結果、正式公開可否のみ",
    },
}


def build_codex_prompt(instruction: str, plan: str, risk: dict[str, Any]) -> str:
    rules = PLAN_RULES.get(plan, PLAN_RULES["Free Plan"])
    return (
        "目的\n"
        f"{instruction.strip() or 'AIOSの小さな改善を行う'}\n\n"
        "対象ファイル\n"
        f"{rules['targets']}\n\n"
        "変更禁止\n"
        f"{rules['forbidden']}\n"
        f"危険度: {risk['risk_level']}\n\n"
        "実装内容\n"
        "1. まず原因または現在状態を確認\n"
        "2. 最小差分で実装\n"
        "3. 既存仕様を壊さない\n\n"
        "確認コマンド\n"
        f"{rules['commands']}\n\n"
        "報告形式\n"
        f"{rules['report']}\n"
    )


def next_step_for(plan: str, risk_level: str) -> str:
    if risk_level == "high":
        return "まず現状確認と差分確認だけを行い、変更前に対象ファイルを絞る"
    if plan == "Release Plan":
        return "本番前チェックを実行し、不足設定を埋める"
    if plan == "Pro Plan":
        return "機能追加の範囲を1つに絞って自動テストまで進める"
    return "現状確認から始めて、小さな修正だけ実行する"

