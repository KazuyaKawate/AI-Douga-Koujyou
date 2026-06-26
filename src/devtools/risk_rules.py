"""Risk level definitions and pattern registry for the Claude Approval Assistant."""
import re

RISK_LEVELS = {
    "safe": {
        "level":          "safe",
        "icon":           "🟢",
        "label":          "安全",
        "color":          "green",
        "recommendation": "yes",
        "rec_label":      "✅ 承認してOK",
        "description":    "読み取り専用、または変更リスクのない操作です。",
    },
    "review": {
        "level":          "review",
        "icon":           "🟡",
        "label":          "確認推奨",
        "color":          "yellow",
        "recommendation": "yes",
        "rec_label":      "🟡 内容確認の上で承認",
        "description":    "変更を伴いますが破壊的ではありません。内容をざっと確認してください。",
    },
    "caution": {
        "level":          "caution",
        "icon":           "🟠",
        "label":          "要注意",
        "color":          "orange",
        "recommendation": "ask_revise",
        "rec_label":      "🟠 Claudeに修正を依頼",
        "description":    "既存データへの影響や元に戻せない変更の可能性があります。慎重に判断してください。",
    },
    "stop": {
        "level":          "stop",
        "icon":           "🔴",
        "label":          "停止",
        "color":          "red",
        "recommendation": "no",
        "rec_label":      "🔴 拒否してください",
        "description":    "破壊的な操作または不可逆な変更です。実行しないでください。",
    },
}

# Order: most specific / most dangerous first.
# Each entry: (risk_level, command_key, regex_pattern, japanese_description)
COMMAND_PATTERNS: list[tuple[str, str, str, str]] = [
    # ── STOP ──────────────────────────────────────────────────────────────────
    ("stop", "rm_rf",             r"rm\s+-rf",                              "rm -rfによる強制削除"),
    ("stop", "remove_critical",   r"Remove-Item.{0,60}(project|config|src/core|pages)\b.{0,30}-Recurse",
                                                                             "重要フォルダの再帰削除"),
    ("stop", "force_push",        r"git\s+push.{0,30}(-f\b|--force)",       "強制プッシュ (git push --force)"),
    ("stop", "reset_hard",        r"git\s+reset\s+--hard",                  "コミット履歴の強制リセット"),
    ("stop", "checkout_overwrite",r"git\s+checkout\s+--\s",                 "ファイルをgit履歴で強制上書き"),
    ("stop", "git_clean",         r"git\s+clean\s+-f",                      "未追跡ファイルの強制削除"),
    ("stop", "env_expose",        r"(?i)(\.env|api.?key\s*=|secret\s*=|password\s*=|bearer.?token)", "シークレット/環境変数の操作"),
    ("stop", "external_api",      r"(?i)(requests\.get|requests\.post|httpx|aiohttp|urllib\.request)",  "外部APIへのHTTPリクエスト"),
    ("stop", "unknown_destructive", r"(?i)(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE)",   "データベース破壊操作"),

    # ── CAUTION ───────────────────────────────────────────────────────────────
    ("caution", "move_rename",    r"Move-Item|Rename-Item|mv\s+pages/",     "ファイル/フォルダの移動・リネーム"),
    ("caution", "remove_item",    r"Remove-Item",                            "ファイル削除 (Remove-Item)"),
    ("caution", "pip_install",    r"pip\d?\s+install",                       "Pythonパッケージのインストール"),
    ("caution", "requirements",   r"requirements\.txt",                      "依存パッケージリスト (requirements.txt) の変更"),
    ("caution", "gitignore",      r"\.gitignore",                            ".gitignoreの変更"),
    ("caution", "core_pipeline",  r"src/(core|pipeline|agents)/",            "コアモジュールの変更"),
    ("caution", "page_renumber",  r"pages/\d{1,2}_.*\.(py|md).*Move|Move.*pages/\d{1,2}_", "既存ページの番号変更"),
    ("caution", "long_command",   r".{300,}",                                "非常に長いコマンド（内容を要確認）"),
    ("caution", "subexpression",  r"\$\(.*\)",                               "PowerShellサブ式（動的コマンド実行）"),

    # ── REVIEW ────────────────────────────────────────────────────────────────
    ("review", "git_push",        r"git\s+push(?!\s.{0,20}--force)(?!\s.{0,5}-f\b)", "GitHubへのプッシュ"),
    ("review", "git_commit",      r"git\s+commit",                           "コミットの作成"),
    ("review", "git_add",         r"git\s+add",                              "変更のステージング (git add)"),
    ("review", "git_merge",       r"git\s+merge",                            "ブランチのマージ"),
    ("review", "write_py",        r"Write.*\.py|New-Item.*\.py",             "Pythonファイルの新規作成"),
    ("review", "write_config",    r"Write.*\.json|Set-Content.*\.json|New-Item.*\.json", "JSONファイルの作成・更新"),
    ("review", "update_app",      r"\bapp\.py\b",                            "メインアプリ (app.py) の更新"),
    ("review", "write_docs",      r"\.(md|rst|txt).*Write|Write.*\.(md|rst|txt)|CHANGELOG|README|ROADMAP", "ドキュメントファイルの更新"),
    ("review", "new_page",        r"pages/\d{1,2}_.*\.py",                   "新しいページファイルの追加"),
    ("review", "config_update",   r"config/[a-z_]+\.json",                   "設定ファイルの更新"),
    ("review", "new_item_file",   r"New-Item.*-ItemType\s+File",             "新規ファイルの作成"),

    # ── SAFE ──────────────────────────────────────────────────────────────────
    ("safe", "git_status",        r"git\s+status",                           "Gitの状態確認"),
    ("safe", "git_log",           r"git\s+log",                              "Gitコミット履歴の確認"),
    ("safe", "git_diff",          r"git\s+diff",                             "差分の確認"),
    ("safe", "git_stash",         r"git\s+stash(?!\s+pop)",                  "変更の一時退避"),
    ("safe", "py_compile",        r"py_compile|python\s+-m\s+py_compile",    "Pythonファイルの構文チェック"),
    ("safe", "health_check",      r"check_project\.py",                       "プロジェクトのヘルスチェック"),
    ("safe", "streamlit_run",     r"streamlit\s+run",                         "Streamlitアプリの起動"),
    ("safe", "read_file",         r"(?:^|\s)Read\b|Get-Content",              "ファイルの読み取り"),
    ("safe", "list_files",        r"Get-ChildItem|(?:^|\s)(ls|dir)\s",        "ファイル一覧の取得"),
    ("safe", "mkdir",             r"New-Item.*-ItemType\s+Directory|mkdir",   "フォルダの新規作成"),
    ("safe", "git_fetch",         r"git\s+fetch",                             "リモートの情報取得（変更なし）"),
    ("safe", "git_stash_pop",     r"git\s+stash\s+pop",                       "退避した変更の復元"),
]

RISK_ORDER = ["stop", "caution", "review", "safe"]


def get_risk_level(command_key: str | None) -> str:
    for pattern_risk, key, *_ in COMMAND_PATTERNS:
        if key == command_key:
            return pattern_risk
    return "review"


def highest_risk(levels: list[str]) -> str:
    for level in RISK_ORDER:
        if level in levels:
            return level
    return "safe"
