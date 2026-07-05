"""AIOS Dev Factory — 開発補助ページ。

Claude Code 不在時でも AIOS で修正案・diff・実装計画を生成できる。
実ファイルは変更しない（読み取り専用）。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Dev Factory", page_icon="🔧", layout="wide")
st.title("🔧 AIOS Dev Factory")
st.caption("Claude Code 不在時でも修正案・unified diff・実装計画を生成する開発補助ツール（ファイル変更なし）")

from dashboard.utils import init_kernel, run_workflow_tracked, get_workflow_output

@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

kernel = _kernel()

# ── ワークフロー選択 ─────────────────────────────────────────────
WORKFLOWS = {
    "dev.code_review":    "🔍 コードレビュー",
    "dev.fix_bug":        "🐛 バグ修正案 + diff",
    "dev.add_feature":    "✨ 機能追加案 + diff",
    "dev.refactor":       "♻️ リファクタリング + diff",
    "dev.implement_plan": "📋 実装計画（複数ファイル）",
}

DESCRIPTIONS = {
    "dev.code_review":    "コードの問題点・改善案を列挙します。ファイルは変更しません。",
    "dev.fix_bug":        "バグ原因を分析し、修正後コードと unified diff を生成します。",
    "dev.add_feature":    "機能追加の実装計画・コード・diff を生成します。",
    "dev.refactor":       "リファクタリング計画・修正コード・diff を生成します。",
    "dev.implement_plan": "複数ファイルにまたがる実装計画・ステップ・リスク評価を生成します。",
}

sel_wf = st.selectbox(
    "実行するタスクを選択",
    list(WORKFLOWS.keys()),
    format_func=lambda k: WORKFLOWS[k],
)
st.caption(DESCRIPTIONS.get(sel_wf, ""))

st.divider()

# ── 入力フォーム ─────────────────────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    instruction = st.text_area(
        "開発指示 *",
        height=130,
        placeholder=(
            "例1（バグ修正）: `get_available_models()` を呼び出すと KeyError が発生する。"
            "レスポンスに 'models' キーがない場合のエラーハンドリングを追加してください。\n\n"
            "例2（機能追加）: AgentRegistry に `search(query)` メソッドを追加して、"
            "agent_id / name / description のいずれかにクエリが含まれる Agent を返すようにしてください。\n\n"
            "例3（リファクタリング）: `analyze()` メソッドが長すぎる。"
            "内部処理を _collect_stats(), _build_report() などのプライベートメソッドに分割してください。"
        ),
        key="dev_instruction",
    )

with col2:
    target_file = st.text_input(
        "対象ファイル（相対パス）",
        placeholder="src/ai_agents/registry.py",
        key="dev_target",
    )
    target_file_2 = st.text_input(
        "関連ファイル2（任意）",
        placeholder="src/ai_agents/definition.py",
        key="dev_target2",
    )

    # ファイル存在確認
    if target_file:
        p = Path(target_file)
        if p.exists():
            stat = p.stat()
            lines = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
            st.success(f"✓ {lines} 行 / {stat.st_size:,} bytes")
        else:
            st.error(f"ファイルが見つかりません: {target_file}")

# ── 実行ボタン ───────────────────────────────────────────────────
run_disabled = not instruction.strip()
if st.button("🚀 実行", type="primary", disabled=run_disabled, use_container_width=True):
    context = {
        "instruction":   instruction,
        "target_file":   target_file or "",
        "target_file_2": target_file_2 or "",
    }

    with st.spinner(f"AI が処理中... ({WORKFLOWS[sel_wf]})"):
        status, dur_sec = run_workflow_tracked(sel_wf, context)

    success = getattr(status, "success", True)

    if success:
        st.success(f"完了 ({dur_sec:.1f}秒)")
    else:
        st.warning(f"一部ステップで問題が発生しました ({dur_sec:.1f}秒)")

    ctx = getattr(status, "context", {})

    # ── unified diff 表示 ─────────────────────────────────────
    diff_text = ctx.get("unified_diff", "")
    if diff_text and not diff_text.startswith("("):
        stats = ctx.get("unified_diff_stats", {})
        col1, col2, col3 = st.columns(3)
        col1.metric("追加行", f"+{stats.get('added', 0)}")
        col2.metric("削除行", f"-{stats.get('removed', 0)}")
        col3.metric("差分(net)", stats.get("net", 0))

        st.subheader("📋 unified diff（適用すべき変更）")
        st.code(diff_text, language="diff")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "💾 .patch ファイルをダウンロード",
                data      = diff_text,
                file_name = f"{Path(target_file).stem if target_file else 'changes'}.patch",
                mime      = "text/plain",
            )
        with col2:
            diff_file = ctx.get("diff_file", "")
            if diff_file:
                st.caption(f"保存済み: `{diff_file}`")

    # ── メインレポート ────────────────────────────────────────
    report_keys = ["dev_report", "review_result", "implementation_plan"]
    report_text = ""
    for k in report_keys:
        v = ctx.get(k, "")
        if v and len(v) > 50:
            report_text = v
            break

    if report_text:
        st.subheader("📄 生成レポート")
        st.markdown(report_text)
        st.download_button(
            "📥 レポートをダウンロード (Markdown)",
            data      = report_text,
            file_name = f"{sel_wf.replace('.', '_')}_report.md",
            mime      = "text/markdown",
        )

    # ── テストコマンド ────────────────────────────────────────
    test_cmd = ctx.get("test_commands", "")
    if test_cmd:
        with st.expander("🧪 テスト計画"):
            st.markdown(test_cmd)

    # ── ステップ詳細 ──────────────────────────────────────────
    with st.expander("🔍 ステップ詳細"):
        step_statuses = getattr(status, "step_statuses", {})
        for sid, ss in step_statuses.items():
            ok  = getattr(ss, "success", True)
            dur = getattr(ss, "duration_ms", 0)
            icon= "✓" if ok else "✗"
            st.write(f"**{icon} {sid}** ({dur}ms)")

st.divider()

# ── 出力ファイル一覧 ──────────────────────────────────────────────
st.subheader("📁 生成済みファイル")

out_dir = Path("output/dev")
if out_dir.exists():
    files = sorted(out_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    if files:
        for f in files[:20]:
            mtime = __import__("datetime").datetime.fromtimestamp(f.stat().st_mtime).strftime("%m/%d %H:%M")
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                icon = "📋" if f.suffix == ".patch" else "📄"
                st.write(f"{icon} `{f.name}`")
                st.caption(mtime)
            with col2:
                content = f.read_text(encoding="utf-8", errors="replace")
                st.download_button(
                    "DL",
                    data      = content,
                    file_name = f.name,
                    mime      = "text/plain",
                    key       = f"dl_{f.stem}",
                )
            with col3:
                if st.button("👁", key=f"view_{f.stem}"):
                    st.session_state[f"show_{f.stem}"] = True

            if st.session_state.get(f"show_{f.stem}"):
                if f.suffix == ".patch":
                    st.code(content, language="diff")
                else:
                    st.markdown(content)
    else:
        st.info("まだ生成ファイルがありません。")
else:
    st.info("output/dev/ ディレクトリがまだ作成されていません。")

# ── 使い方ガイド ──────────────────────────────────────────────────
with st.expander("💡 使い方・Tips"):
    st.markdown("""
## Dev Factory の使い方

### 基本フロー
1. **タスク選択** — 何をしたいか選ぶ
2. **指示入力** — 何を直したいか日本語で具体的に書く
3. **ファイル指定** — 修正対象のファイルパス（プロジェクトルート相対）を入力
4. **実行** — AI が分析して修正案と diff を生成
5. **確認・適用** — diff を見て問題なければ手動で適用、または `.patch` ファイルを使う

### diff の適用方法（手動）
```bash
# patch コマンドで適用（Git プロジェクト）
patch -p1 < output/dev/diff_filename.patch

# または生成されたコードを直接コピーして置き換える
```

### Tips
- **指示は具体的に**: エラーメッセージ・再現手順・期待動作を含めると精度が上がる
- **ファイルは600行まで**: 長いファイルは対象クラスのみ指定を
- **複数ファイルの場合**: `dev.implement_plan` で計画を立ててから個別に `dev.fix_bug` / `dev.add_feature` を使う
- **diff が空の場合**: AI が「変更なし」と判断したか、コードブロック形式で出力されなかった可能性がある

### Workflow 選択ガイド
| タスク | Workflow |
|--------|---------|
| コードを見てほしい | `dev.code_review` |
| エラー・バグを直したい | `dev.fix_bug` |
| 新機能を追加したい | `dev.add_feature` |
| コードをきれいにしたい | `dev.refactor` |
| 何から始めるか計画を立てたい | `dev.implement_plan` |
""")
