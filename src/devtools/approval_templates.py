"""Japanese explanation templates for each command key."""

# Per-command explanations: what, why, after, warnings, next_instruction
TEMPLATES: dict[str, dict] = {
    # ── SAFE ──────────────────────────────────────────────────────────────────
    "git_status": {
        "what":  "Gitの現在の状態を確認します。",
        "why":   "変更されたファイルや未追跡ファイルを把握するためです。",
        "after": "何も変更されません。ターミナルに状態が表示されるだけです。",
        "warnings": [],
        "next_instruction": None,
    },
    "git_log": {
        "what":  "Gitのコミット履歴を一覧表示します。",
        "why":   "過去の変更内容やコミットメッセージを確認するためです。",
        "after": "何も変更されません。履歴が表示されるだけです。",
        "warnings": [],
        "next_instruction": None,
    },
    "git_diff": {
        "what":  "Gitで変更された差分を表示します。",
        "why":   "コミット前にどのファイルが変更されたか確認するためです。",
        "after": "何も変更されません。差分情報が表示されるだけです。",
        "warnings": [],
        "next_instruction": None,
    },
    "git_stash": {
        "what":  "現在の変更を一時退避（スタッシュ）します。",
        "why":   "作業中の変更を保存しつつ、別の作業に切り替えるためです。",
        "after": "ワーキングディレクトリがクリーンになります。変更は `git stash pop` で戻せます。",
        "warnings": ["stashの内容は複数積み重なります。pop忘れに注意"],
        "next_instruction": None,
    },
    "py_compile": {
        "what":  "Pythonファイルの構文エラーを検査します。",
        "why":   "コードが正しく書かれているか、実行前に確認するためです。",
        "after": "エラーがなければ何も起きません。エラーがあればその行を報告します。",
        "warnings": [],
        "next_instruction": None,
    },
    "health_check": {
        "what":  "プロジェクトの必須ファイル・フォルダをすべてチェックします。",
        "why":   "Creator Factory OSが正常に動作するための構成が揃っているか確認するためです。",
        "after": "チェック結果が表示されます。ファイルの変更は行いません。",
        "warnings": [],
        "next_instruction": None,
    },
    "streamlit_run": {
        "what":  "StreamlitアプリをローカルWebサーバーで起動します。",
        "why":   "アプリをブラウザで動作確認するためです。",
        "after": "ブラウザでアプリが開きます。Ctrl+Cで停止できます。",
        "warnings": ["既にポート8501が使用中の場合は別ポートで起動します"],
        "next_instruction": None,
    },
    "read_file": {
        "what":  "ファイルの内容を読み取ります。",
        "why":   "コードや設定の内容を確認するためです。",
        "after": "ファイルの内容が表示されます。変更は行いません。",
        "warnings": [],
        "next_instruction": None,
    },
    "list_files": {
        "what":  "フォルダ内のファイル一覧を取得します。",
        "why":   "プロジェクト構成を確認するためです。",
        "after": "ファイル一覧が表示されます。変更は行いません。",
        "warnings": [],
        "next_instruction": None,
    },
    "mkdir": {
        "what":  "新しいフォルダを作成します。",
        "why":   "モジュールや出力先のディレクトリ構造を整えるためです。",
        "after": "指定したパスにフォルダが作成されます。既存のファイルは変更されません。",
        "warnings": [],
        "next_instruction": None,
    },
    "git_fetch": {
        "what":  "リモートリポジトリの最新情報を取得します（マージはしません）。",
        "why":   "リモートの状態を確認するためです。",
        "after": "ローカルのファイルは変更されません。リモート追跡ブランチが更新されます。",
        "warnings": [],
        "next_instruction": None,
    },

    # ── REVIEW ────────────────────────────────────────────────────────────────
    "git_push": {
        "what":  "ローカルのコミットをGitHubにアップロードします。",
        "why":   "変更をリモートリポジトリに反映させるためです。",
        "after": "GitHubのリポジトリが更新されます。他の人からも変更が見えるようになります。",
        "warnings": ["プッシュ先のブランチ（通常 origin/master）を確認してください",
                     "プッシュ後は取り消しが難しくなります"],
        "next_instruction": None,
    },
    "git_commit": {
        "what":  "ステージング済みの変更をGitコミットとして記録します。",
        "why":   "変更に意味のある履歴を残すためです。",
        "after": "ローカルに新しいコミットが作成されます。GitHubには反映されません（pushが必要）。",
        "warnings": ["コミットメッセージが作業内容を正確に表しているか確認してください"],
        "next_instruction": None,
    },
    "git_add": {
        "what":  "変更したファイルをGitのステージングエリアに追加します。",
        "why":   "次のコミットに含めるファイルを選択するためです。",
        "after": "選択したファイルがステージング状態になります。まだコミットも保存もされません。",
        "warnings": ["`git add .` や `git add -A` は意図しないファイルを含む可能性があります"],
        "next_instruction": None,
    },
    "git_merge": {
        "what":  "別のブランチの変更を現在のブランチに統合します。",
        "why":   "機能ブランチをメインブランチに取り込むためです。",
        "after": "コンフリクトがなければ自動でマージされます。コンフリクトがある場合は手動解決が必要です。",
        "warnings": ["マージ前に両ブランチの最新状態を確認してください",
                     "コンフリクトが起きた場合は慎重に解決してください"],
        "next_instruction": None,
    },
    "write_py": {
        "what":  "新しいPythonファイルを作成します。",
        "why":   "新機能や新しいモジュールを追加するためです。",
        "after": "指定したパスにPythonファイルが作成されます。既存ファイルが同名の場合は上書きされます。",
        "warnings": ["同名ファイルが存在する場合は上書きされます。内容を確認してください"],
        "next_instruction": None,
    },
    "write_config": {
        "what":  "JSONファイルを作成または更新します。",
        "why":   "設定データやアプリケーションのデータを保存するためです。",
        "after": "指定したパスのJSONファイルが更新されます。",
        "warnings": ["既存データが上書きされる可能性があります"],
        "next_instruction": None,
    },
    "update_app": {
        "what":  "アプリケーションのメインファイル (app.py) を変更します。",
        "why":   "バージョン更新・ナビゲーション追加・ワークフロー変更のためです。",
        "after": "アプリの起動時の動作や表示が変わります。",
        "warnings": ["app.pyはすべてのページの起点です。構文エラーはアプリ全体に影響します"],
        "next_instruction": None,
    },
    "write_docs": {
        "what":  "ドキュメントファイル（Markdown等）を作成・更新します。",
        "why":   "README・CHANGELOG・ROADMAPなどのドキュメントを最新化するためです。",
        "after": "指定したMarkdownファイルが更新されます。アプリの動作には影響しません。",
        "warnings": [],
        "next_instruction": None,
    },
    "new_page": {
        "what":  "新しいStreamlitページファイルを作成します。",
        "why":   "新機能のUIページを追加するためです。",
        "after": "Streamlitのサイドバーに新しいページが表示されるようになります。",
        "warnings": ["ページ番号（`NN_`プレフィックス）はサイドバーの表示順に影響します"],
        "next_instruction": None,
    },
    "config_update": {
        "what":  "config/フォルダ内の設定ファイルを更新します。",
        "why":   "アプリケーションの設定やデータを最新化するためです。",
        "after": "次回そのconfigを読み込む際に新しい値が使われます。",
        "warnings": ["既存データのフォーマットが変わる場合はマイグレーションを検討してください"],
        "next_instruction": None,
    },
    "new_item_file": {
        "what":  "新しいファイルを作成します (New-Item)。",
        "why":   "必要なファイルをプロジェクトに追加するためです。",
        "after": "指定パスに新しいファイルが作成されます。",
        "warnings": [],
        "next_instruction": None,
    },
    "git_stash_pop": {
        "what":  "退避（スタッシュ）していた変更を復元します。",
        "why":   "一時保存した作業を再開するためです。",
        "after": "スタッシュの内容がワーキングディレクトリに適用されます。コンフリクトが起きる場合があります。",
        "warnings": ["コンフリクトが起きた場合は手動で解決してください"],
        "next_instruction": None,
    },

    # ── CAUTION ───────────────────────────────────────────────────────────────
    "move_rename": {
        "what":  "ファイルやフォルダの名前または場所を変更します。",
        "why":   "通常はファイルの整理や命名規則の統一のためですが、Claude Codeがページ番号を変更しようとしている可能性があります。",
        "after": "移動・リネーム後は元のパスが存在しなくなります。そのパスを参照している箇所はすべて壊れます。",
        "warnings": [
            "既存ページのリネームはStreamlitのURLを壊します",
            "内部リンク（st.page_link、PAGE_MAPなど）が全て更新が必要になります",
            "ページ番号の変更は禁止ルールです",
        ],
        "next_instruction": "既存ページのリネームは禁止です。新しいページとして別番号で作成してください。例: 「pages/20_XXX.py を新規作成してください」",
    },
    "remove_item": {
        "what":  "ファイルまたはフォルダを削除します (Remove-Item)。",
        "why":   "不要なファイルの整理のためと考えられますが、必要なファイルが削除される可能性があります。",
        "after": "削除したファイルはゴミ箱に入らず、復元が困難です。",
        "warnings": [
            "削除対象のファイルパスを必ず確認してください",
            "config/や src/内のファイルは特に慎重に",
        ],
        "next_instruction": "削除の代わりに、不要なファイルをarchived/フォルダに移動するか、コメントアウトの方法を検討してください。",
    },
    "pip_install": {
        "what":  "Pythonの外部パッケージをインストールします。",
        "why":   "新しいライブラリをプロジェクトで使えるようにするためです。",
        "after": "システムのPython環境にパッケージが追加されます。requirements.txtへの記載が必要です。",
        "warnings": [
            "インストール後はrequirements.txtに追記してください",
            "仮想環境（venv）が有効になっているか確認してください",
        ],
        "next_instruction": "インストール後に `pip freeze > requirements.txt` か、requirements.txtへの手動追記もお願いしてください。",
    },
    "requirements": {
        "what":  "requirements.txt（依存パッケージリスト）を変更します。",
        "why":   "プロジェクトの依存関係を更新するためです。",
        "after": "次回 `pip install -r requirements.txt` を実行すると変更が反映されます。",
        "warnings": ["バージョン固定（==）を推奨します。>=は将来の非互換変更を引き込む可能性があります"],
        "next_instruction": None,
    },
    "gitignore": {
        "what":  ".gitignoreを変更します（Gitが無視するファイルのリスト）。",
        "why":   "機密ファイルやビルド成果物をGitの追跡から除外するためです。",
        "after": ".gitignoreに追加したパターンにマッチするファイルはGitに含まれなくなります。",
        "warnings": [
            "すでに追跡中のファイルは.gitignoreを追加しても追跡が続きます（git rm --cachedが必要）",
            ".envなどのシークレットが正しく除外されているか確認してください",
        ],
        "next_instruction": None,
    },
    "core_pipeline": {
        "what":  "src/core/ または src/pipeline/ の中核モジュールを変更します。",
        "why":   "既存の動画制作パイプラインのバグ修正や機能追加のためと考えられます。",
        "after": "変更によっては既存の動画生成フローが壊れる可能性があります。",
        "warnings": [
            "コアモジュールの変更は既存機能全体に影響します",
            "変更前に現在の動作を確認し、変更後にヘルスチェックを実行してください",
        ],
        "next_instruction": "コアモジュールを変更する前に、変更内容と影響範囲を説明してください。",
    },
    "page_renumber": {
        "what":  "既存ページファイルの番号を変更しようとしています。",
        "why":   "Claude Codeがページ順序の整理を試みている可能性があります。",
        "after": "Streamlitのサイドバー順序が変わり、既存のリンクがすべて壊れます。",
        "warnings": [
            "これはプロジェクトの禁止ルールです",
            "PAGE_MAP、NAV_ITEMS、st.page_linkが全て壊れます",
        ],
        "next_instruction": "既存ページのリネームや番号変更は禁止です。新しいページを新しい番号で作成してください。",
    },
    "long_command": {
        "what":  "非常に長いコマンドが検出されました。",
        "why":   "複数の操作をまとめて実行しようとしている可能性があります。",
        "after": "実行結果が複雑になる可能性があります。",
        "warnings": ["コマンドが長すぎて内容の静的検証が困難です。内容を分割して実行することを推奨します"],
        "next_instruction": "コマンドを複数の小さなステップに分割してください。一度に確認できる量で実行してください。",
    },
    "subexpression": {
        "what":  "PowerShellのサブ式 $(...) を含むコマンドです。動的にコマンドが生成されます。",
        "why":   "動的なファイルリストや条件に基づいた操作のためです。",
        "after": "実行時に動的に変化する可能性があるため、静的に内容を確認できません。",
        "warnings": ["サブ式の内容をよく確認してから実行してください"],
        "next_instruction": None,
    },

    # ── STOP ──────────────────────────────────────────────────────────────────
    "rm_rf": {
        "what":  "rm -rf でファイルまたはフォルダを強制的に再帰削除しようとしています。",
        "why":   "Claude Codeが不要なファイルを削除しようとしていますが、これは危険です。",
        "after": "削除されたファイルは復元できません。プロジェクト全体が失われる可能性があります。",
        "warnings": ["絶対に承認しないでください", "rm -rfは取り消しできません"],
        "next_instruction": "rm -rf は絶対に使わないでください。削除が必要な場合は具体的なファイル名を指定してRemove-Itemを使用してください。",
    },
    "remove_critical": {
        "what":  "project/・config/・src/などの重要フォルダを再帰削除しようとしています。",
        "why":   "誤った操作またはClaudeの判断ミスです。",
        "after": "プロジェクトのすべてのデータが失われます。",
        "warnings": ["絶対に承認しないでください", "このフォルダはプロジェクトの中核です"],
        "next_instruction": "重要フォルダの削除を停止してください。削除が必要な理由を説明した上で、具体的なファイルのみを対象にしてください。",
    },
    "force_push": {
        "what":  "git push --force でGitHubのコミット履歴を強制上書きしようとしています。",
        "why":   "履歴の書き換え後にリモートと同期するためですが、非常に危険です。",
        "after": "GitHubのコミット履歴が上書きされます。他のメンバーの作業が失われる可能性があります。",
        "warnings": ["フォースプッシュは取り消しが非常に困難です", "mainブランチへのフォースプッシュは禁止です"],
        "next_instruction": "force pushは禁止です。通常の git push origin master を使用してください。履歴の問題がある場合は内容を説明してください。",
    },
    "reset_hard": {
        "what":  "git reset --hard でコミット履歴とワーキングディレクトリを強制リセットします。",
        "why":   "コミットを取り消すためですが、未コミットの作業が全て失われます。",
        "after": "指定したコミットより後の変更が全て消えます。取り消しはほぼ不可能です。",
        "warnings": ["未コミットの変更が全て失われます", "git reflogで復元できる場合がありますが保証はありません"],
        "next_instruction": "reset --hard の代わりに git revert を使用してください。特定のコミットを取り消すことができます。",
    },
    "checkout_overwrite": {
        "what":  "git checkout -- でワーキングディレクトリのファイルをGit履歴で強制上書きします。",
        "why":   "未コミットの変更を捨てるためですが、その変更は永久に失われます。",
        "after": "指定ファイルの未コミット変更が全て消えます。",
        "warnings": ["この操作は取り消せません", "未コミットの作業を失う前に内容を確認してください"],
        "next_instruction": "checkout -- の代わりに git stash を使用して変更を退避してください。必要になったら git stash pop で戻せます。",
    },
    "git_clean": {
        "what":  "git clean -f で未追跡ファイルを強制削除します。",
        "why":   "ワーキングディレクトリをきれいにするためですが、新規作成ファイルが消えます。",
        "after": "Gitで追跡されていないファイルが全て削除されます。",
        "warnings": ["新規作成したファイルが削除されます", "取り消しできません"],
        "next_instruction": "git clean の代わりに git status で不要ファイルを確認してから、個別に削除してください。",
    },
    "env_expose": {
        "what":  ".env ファイルやAPIキー・シークレットに関する操作が検出されました。",
        "why":   "設定の読み込みまたは誤ってシークレットを含む操作の可能性があります。",
        "after": "シークレットがGitHubや出力に露出すると、セキュリティリスクになります。",
        "warnings": [
            ".env はGitにコミットしてはいけません",
            "APIキーが出力されるコマンドを実行しないでください",
        ],
        "next_instruction": ".envや機密情報を含む操作を止めてください。環境変数は os.environ.get() で安全に読み込んでください。",
    },
    "external_api": {
        "what":  "外部APIへのHTTPリクエストが検出されました。",
        "why":   "外部サービスとの連携コードが実行されようとしています。",
        "after": "外部サーバーにリクエストが送信されます。APIキーや料金に注意してください。",
        "warnings": [
            "このプロジェクトは「外部API不使用」がルールです",
            "意図しないAPIコストが発生する可能性があります",
        ],
        "next_instruction": "外部APIの呼び出しを行わないでください。ルールベースまたはローカル処理で実装してください。",
    },
    "unknown_destructive": {
        "what":  "破壊的なデータベース操作またはデータ削除コマンドが検出されました。",
        "why":   "SQLまたはデータ操作コマンドの実行が試みられています。",
        "after": "データが永久に失われる可能性があります。",
        "warnings": ["このコマンドの実行は止めてください"],
        "next_instruction": "このコマンドを実行せずに、代替手段を提案してください。",
    },
}

# Fallback template for unrecognized patterns
DEFAULT_TEMPLATE = {
    "what":  "コマンドの内容を自動判定できませんでした。",
    "why":   "入力テキストから操作の目的を特定できませんでした。",
    "after": "実行結果が不明です。承認前に内容を手動で確認してください。",
    "warnings": ["自動解析が不完全です。コマンド全文を目視で確認してください"],
    "next_instruction": "コマンドの内容を日本語で説明してから実行してください。",
}


def get_template(command_key: str) -> dict:
    return TEMPLATES.get(command_key, DEFAULT_TEMPLATE)


def get_recommendation_text(recommendation: str) -> str:
    return {
        "yes":         "✅ 承認してOKです",
        "ask_revise":  "🟠 Claudeに修正・代替案を依頼してください",
        "no":          "🔴 拒否してください。このコマンドを実行しないでください",
    }.get(recommendation, "🟡 内容を確認の上で判断してください")
