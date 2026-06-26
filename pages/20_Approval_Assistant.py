"""
Claude承認アシスタント — Creator Factory OS v4.4.1
Translates Claude Code approval prompts into Japanese and classifies risk.
No external API calls. Rule-based classification only.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.devtools.approval_analyzer import analyze, load_history, clear_history, get_latest_risk
from src.devtools.risk_rules import RISK_LEVELS

APP_VERSION = "4.4.1"

st.set_page_config(
    page_title="Claude承認アシスタント | Creator Factory OS",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Claude承認アシスタント")
st.caption(
    f"Claude Codeの確認プロンプトを日本語に翻訳し、リスクを分類します。"
    f" | Creator Factory OS v{APP_VERSION}"
)

tab_analyze, tab_history, tab_guide = st.tabs(["🔍 分析", "📋 履歴", "📖 ガイド"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab_analyze:
    st.markdown(
        "Claude Codeが承認を求めてきたプロンプトを下のテキストエリアに貼り付けて「分析」ボタンを押してください。"
    )

    raw_input = st.text_area(
        "Claude Codeの確認文を貼り付け",
        height=180,
        placeholder=(
            "例:\n"
            "Bash\n"
            "Description: Run shell command\n"
            "Command: git push origin master\n\n"
            "または PowerShell コマンドをそのまま貼り付けてください。"
        ),
        key="raw_prompt_input",
    )

    col_analyze, col_clear = st.columns([2, 1])
    with col_analyze:
        analyze_btn = st.button("🔍 分析する", type="primary", use_container_width=True)
    with col_clear:
        if st.button("🗑️ クリア", use_container_width=True):
            st.session_state.pop("analysis_result", None)
            st.rerun()

    if analyze_btn:
        if not raw_input.strip():
            st.warning("テキストを入力してください。")
        else:
            with st.spinner("分析中..."):
                result = analyze(raw_input)
            st.session_state["analysis_result"] = result
            st.rerun()

    # ── Display result ──────────────────────────────────────────────────────
    result = st.session_state.get("analysis_result")

    if result and result.get("risk_level"):
        st.divider()

        risk_key = result["risk_level"]
        risk_info = RISK_LEVELS[risk_key]
        icon = result["risk_icon"]
        label = result["risk_label"]

        # Risk badge
        RISK_COLORS = {
            "safe":    "success",
            "review":  "warning",
            "caution": "warning",
            "stop":    "error",
        }
        badge_fn = getattr(st, RISK_COLORS.get(risk_key, "info"))

        badge_fn(
            f"**{icon} 危険度: {label}** — {result['risk_description']}"
        )

        st.divider()

        # Main analysis columns
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown("### 📋 分析結果")

            with st.container(border=True):
                st.markdown("**🎯 やろうとしていること**")
                st.markdown(result["what_it_does"] or "—")

            with st.container(border=True):
                st.markdown("**❓ なぜ必要か**")
                st.markdown(result["why_needed"] or "—")

            with st.container(border=True):
                st.markdown("**⚡ 実行後に起こること**")
                st.markdown(result["what_happens_after"] or "—")

            if result.get("warnings"):
                with st.container(border=True):
                    st.markdown("**⚠️ 注意点**")
                    for w in result["warnings"]:
                        st.markdown(f"- {w}")

        with col_right:
            st.markdown("### 🧭 推奨判断")

            rec = result["recommendation"]
            if rec == "yes":
                st.success(result["recommendation_text"])
            elif rec == "ask_revise":
                st.warning(result["recommendation_text"])
            else:
                st.error(result["recommendation_text"])

            st.divider()

            st.markdown("**🔎 検出されたコマンドパターン**")
            matches = result.get("classified_commands", [])
            if matches:
                for m in matches[:6]:
                    risk_emoji = {"stop": "🔴", "caution": "🟠", "review": "🟡", "safe": "🟢"}.get(m["risk"], "⚪")
                    st.caption(f"{risk_emoji} {m['description']}")
            else:
                st.caption("パターンが検出されませんでした。")

            if result.get("file_paths"):
                st.divider()
                st.markdown("**📁 検出されたファイルパス**")
                for fp in result["file_paths"][:8]:
                    st.caption(f"• {fp}")

        st.divider()

        # Next instruction
        st.markdown("### 💬 次に送る指示案")
        if result.get("next_instruction"):
            next_inst = result["next_instruction"]
            st.text_area(
                "Claudeへのメッセージ（コピーして使用してください）",
                value=next_inst,
                height=100,
                key="next_instruction_display",
            )
        else:
            if rec == "yes":
                st.success("このコマンドは承認して問題ありません。特別な指示は不要です。")
            else:
                st.info("上の「注意点」を参考にClaudeへの指示を作成してください。")

        st.divider()

        # Raw prompt summary
        with st.expander("📄 入力テキスト（確認用）", expanded=False):
            st.text(result.get("raw_prompt", "")[:1000])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════

with tab_history:
    st.subheader("📋 分析履歴")
    st.caption("過去100件の分析結果を保存しています。")

    history = load_history(50)

    hcol1, hcol2 = st.columns([3, 1])
    with hcol2:
        if st.button("🗑️ 履歴をクリア", use_container_width=True):
            clear_history()
            st.success("履歴を削除しました")
            st.rerun()

    if not history:
        st.info("まだ分析履歴がありません。「分析」タブでプロンプトを分析してください。")
    else:
        st.caption(f"{len(history)} 件の履歴")

        # Risk level filter
        risk_filter = st.selectbox(
            "危険度で絞り込み",
            ["すべて", "🔴 停止", "🟠 要注意", "🟡 確認推奨", "🟢 安全"],
            key="history_filter",
        )
        filter_map = {
            "すべて": None,
            "🔴 停止": "stop",
            "🟠 要注意": "caution",
            "🟡 確認推奨": "review",
            "🟢 安全": "safe",
        }
        filter_key = filter_map[risk_filter]
        filtered_history = [
            h for h in history
            if filter_key is None or h.get("risk_level") == filter_key
        ]

        for entry in filtered_history:
            risk_lv = entry.get("risk_level", "safe")
            icon = entry.get("risk_icon", "🟢")
            label = RISK_LEVELS.get(risk_lv, {}).get("label", risk_lv)
            ts = entry.get("timestamp", "")[:16].replace("T", " ")
            summary = entry.get("summary", "")

            with st.expander(f"{icon} {ts} — {summary[:60]}", expanded=False):
                hc1, hc2 = st.columns([3, 1])
                with hc1:
                    st.caption(f"**危険度:** {icon} {label}")
                    st.caption(f"**推奨:** {entry.get('recommendation', '')}")
                    if entry.get("warnings"):
                        st.markdown("**注意点:**")
                        for w in entry["warnings"]:
                            st.caption(f"- {w}")
                with hc2:
                    st.caption(f"**ID:** {entry.get('id', '')}")
                    st.caption(f"**時刻:** {ts}")
                with st.expander("元テキスト"):
                    st.text(entry.get("raw_prompt", "")[:500])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GUIDE
# ══════════════════════════════════════════════════════════════════════════════

with tab_guide:
    st.subheader("📖 使い方ガイド")

    st.markdown("""
## 🔍 Claude承認アシスタントとは？

Claude Codeが操作の承認を求めてきたとき、何が起きるのか素早く判断するためのツールです。
**外部APIは一切使用しません。** すべてルールベースで解析します。

---

## ⚙️ 使い方

1. Claude Codeが「承認が必要です」と表示したプロンプトをコピー
2. 「分析」タブのテキストエリアに貼り付け
3. 「🔍 分析する」ボタンをクリック
4. 結果を見て承認 / 拒否 / 修正依頼を判断

---

## 🚦 危険度の基準

| レベル | 意味 | 対応 |
|--------|------|------|
| 🟢 安全 | 読み取り専用・変更リスクなし | そのまま承認 |
| 🟡 確認推奨 | 変更あり・破壊的でない | 内容確認の上で承認 |
| 🟠 要注意 | 既存データへの影響あり | Claudeに修正を依頼 |
| 🔴 停止 | 破壊的・不可逆な操作 | 必ず拒否 |

---

## 🟢 安全なコマンド例

```
git status / git log / git diff
py_compile で構文チェック
check_project.py ヘルスチェック
Read / Get-Content でファイル読み取り
Get-ChildItem / ls でファイル一覧
New-Item -ItemType Directory でフォルダ作成
streamlit run でアプリ起動
```

## 🟡 確認推奨なコマンド例

```
git add / git commit / git push
新しいPythonファイル・JSONファイルの作成
app.py の更新
ドキュメント (.md) の更新
新しいページ (pages/NN_XXX.py) の追加
```

## 🟠 要注意なコマンド例

```
Move-Item / Rename-Item (ファイル移動・リネーム)
Remove-Item (ファイル削除)
pip install (パッケージインストール)
requirements.txt の変更
src/core/ や src/pipeline/ の変更
```

## 🔴 停止すべきコマンド例

```
rm -rf / Remove-Item -Recurse (重要フォルダ削除)
git push --force (強制プッシュ)
git reset --hard (コミット履歴の強制リセット)
git checkout -- . (ファイルの強制上書き)
.env やAPIキーの操作
外部APIへのHTTPリクエスト
```

---

## ⚠️ このプロジェクトの禁止ルール

1. **既存ページのリネーム禁止** — `pages/NN_XXX.py` の番号変更はリンクを壊します
2. **外部API呼び出し禁止** — すべてローカル処理・ルールベース
3. **既存ファクトリーの動作変更禁止** — additive changesのみ
4. **force push禁止** — git push --force は使用しない
5. **rm -rf禁止** — Remove-Itemで具体的なファイルを指定する

---

## 💡 ヒント

- 長い PowerShell コマンドは `$()` サブ式を含む場合があります。内容を確認してください。
- `git add .` より `git add 具体的なファイル名` のほうが安全です。
- ファイルを削除するより、まず `archived/` フォルダへの移動を検討してください。
""")

    st.divider()

    # Risk level legend
    st.subheader("🚦 危険度レベル一覧")
    for level_key, info in RISK_LEVELS.items():
        with st.container(border=True):
            lc1, lc2 = st.columns([1, 5])
            lc1.markdown(f"# {info['icon']}")
            with lc2:
                st.markdown(f"**{info['label']}** — {info['rec_label']}")
                st.caption(info["description"])
