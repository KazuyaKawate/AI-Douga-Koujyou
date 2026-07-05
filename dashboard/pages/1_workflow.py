"""Workflow 実行ページ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.utils import init_kernel, run_workflow_tracked, get_workflow_output, FACTORY_ICONS

st.set_page_config(page_title="Workflow 実行", page_icon="⚡", layout="wide")
st.title("⚡ Workflow 実行")

@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

kernel = _kernel()
all_wf = sorted(kernel.registry.list_workflows())

# ── Factory フィルタ ─────────────────────────────────────────────
factories = sorted({w.split(".")[0] for w in all_wf})
selected_factory = st.selectbox(
    "Factory を選択",
    ["すべて"] + factories,
    format_func=lambda f: f if f == "すべて" else f"{FACTORY_ICONS.get(f,'🔧')} {f}",
)

if selected_factory != "すべて":
    wf_list = [w for w in all_wf if w.startswith(selected_factory + ".")]
else:
    wf_list = all_wf

selected_wf = st.selectbox("Workflow を選択", wf_list)

st.divider()

# ── コンテキスト入力 ─────────────────────────────────────────────
st.subheader("入力パラメータ")

wf_def = kernel.registry.get_workflow(selected_wf)
if wf_def and hasattr(wf_def, "default_context"):
    default_ctx = wf_def.default_context or {}
else:
    default_ctx = {}

# Factory の default_context を取得
fid = selected_wf.split(".")[0]
factory = kernel.registry.get_factory(fid)
if factory and hasattr(factory, "_manifest"):
    factory_ctx = factory._manifest.get("default_context", {})
    for k, v in factory_ctx.items():
        if k not in default_ctx:
            default_ctx[k] = v

# 主要パラメータのフォーム
with st.form("run_form"):
    context_inputs = {}

    # 共通パラメータ
    common_keys = ["topic", "theme", "goal", "keyword", "target", "tone", "style"]

    col1, col2 = st.columns(2)
    param_count = 0

    all_keys = list(default_ctx.keys())
    if not all_keys:
        all_keys = ["topic"]

    for key in all_keys[:6]:
        val = default_ctx.get(key, "")
        col = col1 if param_count % 2 == 0 else col2
        with col:
            context_inputs[key] = st.text_input(
                key,
                value=str(val),
                placeholder=f"{key} を入力...",
            )
        param_count += 1

    # 追加パラメータ（JSON）
    extra_json = st.text_area(
        "追加パラメータ (JSON)",
        value="{}",
        height=80,
        help="例: {\"language\": \"Japanese\", \"max_length\": 500}",
    )

    run_btn = st.form_submit_button("▶ Workflow 実行", type="primary", use_container_width=True)

if run_btn:
    import json
    context = {k: v for k, v in context_inputs.items() if v}
    try:
        extra = json.loads(extra_json)
        context.update(extra)
    except Exception:
        pass

    with st.spinner(f"実行中: {selected_wf} ..."):
        status, dur_sec = run_workflow_tracked(selected_wf, context)

    success = getattr(status, "success", True)
    if success:
        st.success(f"完了 ({dur_sec:.1f}秒)")
    else:
        st.error(f"失敗 ({dur_sec:.1f}秒)")

    # 結果表示
    output = get_workflow_output(status)
    if output:
        st.subheader("生成結果")
        st.markdown(output)
        st.download_button(
            "📥 結果をダウンロード",
            data=output,
            file_name=f"{selected_wf.replace('.','_')}_output.md",
            mime="text/markdown",
        )

    # ステップ詳細
    with st.expander("ステップ詳細"):
        step_statuses = getattr(status, "step_statuses", {})
        for step_id, step_s in step_statuses.items():
            step_ok = getattr(step_s, "success", True)
            icon    = "✓" if step_ok else "✗"
            dur     = getattr(step_s, "duration_ms", 0)
            st.write(f"**{icon} {step_id}** ({dur}ms)")
            out = getattr(step_s, "output", None)
            if out:
                st.code(str(out)[:500], language=None)

st.divider()

# ── Workflow 一覧 ────────────────────────────────────────────────
with st.expander("登録済み Workflow 一覧"):
    for wf in all_wf:
        fid_  = wf.split(".")[0]
        icon_ = FACTORY_ICONS.get(fid_, "🔧")
        st.write(f"{icon_} `{wf}`")
