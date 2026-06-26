import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.utils.character_manager import load_characters
from src.utils.background_manager import load_backgrounds
from src.director.director_planner import load_director_plan
from src.utils.prompt_builder import (
    CAMERA_OPTIONS,
    MOOD_OPTIONS,
    OUTPUT_TYPES,
    STYLE_OPTIONS,
    TEMPLATES_PATH,
    add_template,
    build_prompt,
    delete_template,
    duplicate_template,
    get_template,
    load_templates,
    update_template,
)

st.set_page_config(page_title="プロンプトビルダー", page_icon="📝", layout="wide")
st.title("📝 プロンプトビルダー")
st.caption("キャラクター・背景・ムード・スタイルを組み合わせてプロンプトを生成・保存 | v2.9")

_settings = load_settings()

# Session state defaults
for _key, _default in [
    ("pb_prompt_text", ""),
    ("pb_negative", ""),
    ("pb_selected_id", None),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ── Load-from-template signal (set by sidebar buttons, consumed here) ──────────

if "pb_load_id" in st.session_state:
    _tid = st.session_state.pop("pb_load_id")
    _tmpl = get_template(_tid)
    if _tmpl:
        st.session_state["pb_output_type"]  = _tmpl.get("output_type", OUTPUT_TYPES[0])
        st.session_state["pb_mood"]         = _tmpl.get("mood", MOOD_OPTIONS[0])
        st.session_state["pb_camera"]       = _tmpl.get("camera", CAMERA_OPTIONS[0])
        st.session_state["pb_style"]        = _tmpl.get("style", STYLE_OPTIONS[0])
        st.session_state["pb_char_id"]      = _tmpl.get("character_id")
        st.session_state["pb_bg_id"]        = _tmpl.get("background_id")
        st.session_state["pb_prompt_text"]  = _tmpl.get("prompt_text", "")
        st.session_state["pb_negative"]     = _tmpl.get("negative_prompt", "")
        st.session_state["pb_selected_id"]  = _tid


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    tmpl_data = load_templates()
    tmpls     = tmpl_data["templates"]

    st.subheader(f"💾 保存済みテンプレート  ({len(tmpls)})")
    if not tmpls:
        st.caption("まだテンプレートがありません")
    else:
        for t in tmpls:
            is_sel = t["id"] == st.session_state["pb_selected_id"]
            label  = t["name"]
            otype  = t.get("output_type", "")
            if otype:
                label += f"\n{otype}"
            if st.button(
                label,
                key=f"load_{t['id']}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state["pb_load_id"] = t["id"]
                st.rerun()

    st.divider()

    # ── Director Plan scene injection ──────────────────────────────────────────
    with st.expander("🎬 演出ディレクション"):
        _pb_project = PROJECT_ROOT / "project"
        _pb_dir_eps = sorted([
            d for d in _pb_project.iterdir()
            if d.is_dir() and (d / "director_plan.json").exists()
        ], key=lambda d: d.name) if _pb_project.exists() else []

        if not _pb_dir_eps:
            st.caption("演出計画がありません")
            st.caption("🎬 AI Director で作成してください")
        else:
            _pb_dir_ep_names = [d.name for d in _pb_dir_eps]
            _pb_sel_dir_ep   = st.selectbox(
                "EP",
                _pb_dir_ep_names,
                key="pb_dir_ep_sel",
                label_visibility="collapsed",
            )
            _pb_dir_plan = load_director_plan(_pb_project / _pb_sel_dir_ep) if _pb_sel_dir_ep else None
            if _pb_dir_plan and _pb_dir_plan.get("scenes"):
                _pb_dir_scenes     = _pb_dir_plan["scenes"]
                _pb_dir_scene_opts = [
                    f"S{s['scene_no']}: {s.get('scene_goal', '（未設定）')[:25]}"
                    for s in _pb_dir_scenes
                ]
                _pb_sel_scene_i = st.selectbox(
                    "Scene",
                    range(len(_pb_dir_scene_opts)),
                    format_func=lambda i: _pb_dir_scene_opts[i],
                    key="pb_dir_scene_sel",
                    label_visibility="collapsed",
                )
                _pb_cur_scene = st.session_state.get("pb_director_scene", {})
                if _pb_cur_scene:
                    st.caption(f"✅ 適用中: S{_pb_cur_scene.get('scene_no','')}")
                if st.button("🎬 演出を適用", use_container_width=True, key="pb_dir_apply"):
                    st.session_state["pb_director_scene"]   = _pb_dir_scenes[_pb_sel_scene_i]
                    st.session_state["pb_director_ep_id"]   = _pb_sel_dir_ep
                    st.rerun()
                if _pb_cur_scene:
                    if st.button("❌ クリア", use_container_width=True, key="pb_dir_clear_sb"):
                        st.session_state.pop("pb_director_scene", None)
                        st.session_state.pop("pb_director_ep_id", None)
                        st.rerun()
            else:
                st.caption("シーンがありません")

    st.divider()
    st.caption(f"⚙️ `{_settings['ai']['model']}` | `{TEMPLATES_PATH.name}`")


# ── Load shared data ───────────────────────────────────────────────────────────

char_data = load_characters()
all_chars = char_data["characters"]
char_id_opts  = [None] + [c["id"] for c in all_chars]
char_name_map = {None: "（なし）"}
char_name_map.update({c["id"]: c["basic"]["display_name"] for c in all_chars})

bg_data  = load_backgrounds()
all_bgs  = bg_data["backgrounds"]
bg_id_opts  = [None] + [b["id"] for b in all_bgs]
bg_name_map = {None: "（なし）"}
bg_name_map.update({b["id"]: b["basic"]["display_name"] for b in all_bgs})


# ── Settings panel ─────────────────────────────────────────────────────────────

st.subheader("⚙️ プロンプト設定")

row1_c1, row1_c2 = st.columns(2)

with row1_c1:
    # Character selectbox — respects pb_char_id if set via template load
    _char_sel_idx = 0
    if st.session_state.get("pb_char_id") in char_id_opts:
        _char_sel_idx = char_id_opts.index(st.session_state["pb_char_id"])

    sel_char_id = st.selectbox(
        "🧑 キャラクター",
        char_id_opts,
        format_func=lambda x: char_name_map.get(x, "不明"),
        index=_char_sel_idx,
        key="pb_char_sel",
    )

with row1_c2:
    _bg_sel_idx = 0
    if st.session_state.get("pb_bg_id") in bg_id_opts:
        _bg_sel_idx = bg_id_opts.index(st.session_state["pb_bg_id"])

    sel_bg_id = st.selectbox(
        "🏞️ 背景・シーン",
        bg_id_opts,
        format_func=lambda x: bg_name_map.get(x, "不明"),
        index=_bg_sel_idx,
        key="pb_bg_sel",
    )

row2_c1, row2_c2, row2_c3 = st.columns(3)

with row2_c1:
    _ot_val = st.session_state.get("pb_output_type", OUTPUT_TYPES[0])
    _ot_idx = OUTPUT_TYPES.index(_ot_val) if _ot_val in OUTPUT_TYPES else 0
    sel_output_type = st.selectbox(
        "📤 出力タイプ",
        OUTPUT_TYPES,
        index=_ot_idx,
        key="pb_output_type",
    )

with row2_c2:
    _mood_val = st.session_state.get("pb_mood", MOOD_OPTIONS[0])
    _mood_idx = MOOD_OPTIONS.index(_mood_val) if _mood_val in MOOD_OPTIONS else 0
    sel_mood = st.selectbox(
        "🎭 ムード",
        MOOD_OPTIONS,
        index=_mood_idx,
        key="pb_mood",
    )

with row2_c3:
    _style_val = st.session_state.get("pb_style", STYLE_OPTIONS[0])
    _style_idx = STYLE_OPTIONS.index(_style_val) if _style_val in STYLE_OPTIONS else 0
    sel_style = st.selectbox(
        "🎨 スタイル",
        STYLE_OPTIONS,
        index=_style_idx,
        key="pb_style",
    )

row3_c1, row3_c2 = st.columns(2)

with row3_c1:
    _cam_val = st.session_state.get("pb_camera", CAMERA_OPTIONS[0])
    _cam_idx = CAMERA_OPTIONS.index(_cam_val) if _cam_val in CAMERA_OPTIONS else 0
    sel_camera = st.selectbox(
        "🎥 カメラ",
        CAMERA_OPTIONS,
        index=_cam_idx,
        key="pb_camera",
    )

with row3_c2:
    notes_input = st.text_input(
        "📌 ノート（任意）",
        value=st.session_state.get("pb_notes", ""),
        key="pb_notes_input",
        placeholder="例: 第3話用、モノローグシーン向け",
    )

# Resolve selected character/background dicts
sel_char = next((c for c in all_chars if c["id"] == sel_char_id), None)
sel_bg   = next((b for b in all_bgs   if b["id"] == sel_bg_id),   None)

gen_col, _ = st.columns([2, 3])
with gen_col:
    generate_btn = st.button(
        "🔧 プロンプトを生成",
        type="primary",
        use_container_width=True,
    )

if generate_btn:
    prompt_text, negative = build_prompt(
        output_type=sel_output_type,
        mood=sel_mood,
        camera=sel_camera,
        style=sel_style,
        character=sel_char,
        background=sel_bg,
    )
    st.session_state["pb_prompt_text"] = prompt_text
    st.session_state["pb_negative"]    = negative
    st.session_state["pb_selected_id"] = None  # generated fresh, not from a template
    st.session_state["pb_char_id"]     = sel_char_id
    st.session_state["pb_bg_id"]       = sel_bg_id


# ── Prompt output ──────────────────────────────────────────────────────────────

prompt_text = st.session_state["pb_prompt_text"]
negative    = st.session_state["pb_negative"]

if prompt_text:
    st.divider()
    st.subheader("📋 生成プロンプト")

    out_c1, out_c2 = st.columns([3, 1])
    with out_c1:
        st.caption(f"**{sel_output_type}**")
        st.code(prompt_text, language=None)
    with out_c2:
        st.download_button(
            "⬇️ .txt でダウンロード",
            data=prompt_text,
            file_name=f"prompt_{sel_output_type[:10].replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        char_lbl = sel_char["basic"]["display_name"] if sel_char else "（なし）"
        bg_lbl   = sel_bg["basic"]["display_name"]   if sel_bg   else "（なし）"
        st.caption(f"キャラクター: {char_lbl}")
        st.caption(f"背景: {bg_lbl}")
        st.caption(f"ムード: {sel_mood}")
        st.caption(f"カメラ: {sel_camera}")
        st.caption(f"スタイル: {sel_style}")

    if negative:
        with st.expander("🚫 ネガティブプロンプト"):
            st.code(negative, language=None)
            st.download_button(
                "⬇️ ネガティブ .txt",
                data=negative,
                file_name="negative_prompt.txt",
                mime="text/plain",
                key="dl_neg",
                use_container_width=True,
            )

    # ── Director scene injection ───────────────────────────────────────────────

    _pb_d_scene = st.session_state.get("pb_director_scene")
    _pb_d_ep_id = st.session_state.get("pb_director_ep_id", "")
    if _pb_d_scene:
        st.divider()
        dir_hdr, dir_clr = st.columns([5, 1])
        dir_hdr.subheader(f"🎬 演出ディレクション: {_pb_d_ep_id} S{_pb_d_scene.get('scene_no','')}")
        if dir_clr.button("❌", key="pb_dir_clear_main"):
            st.session_state.pop("pb_director_scene", None)
            st.session_state.pop("pb_director_ep_id", None)
            st.rerun()

        dc1, dc2 = st.columns(2)
        with dc1:
            if _pb_d_scene.get("scene_goal"):
                st.caption(f"ゴール: {_pb_d_scene['scene_goal']}")
            if _pb_d_scene.get("emotion"):
                st.caption(f"感情: {_pb_d_scene['emotion']}")
            if _pb_d_scene.get("camera_angle"):
                st.caption(f"カメラ: {_pb_d_scene['camera_angle']} / {_pb_d_scene.get('camera_motion','')}")
            if _pb_d_scene.get("lighting"):
                st.caption(f"ライティング: {_pb_d_scene['lighting']}")

        # Pick direction text based on output type
        _dir_dir_text = _pb_d_scene.get("image_prompt_direction", "")
        if "動画" in (sel_output_type or ""):
            _dir_dir_text = _pb_d_scene.get("video_prompt_direction", "") or _dir_dir_text
        elif "ボイス" in (sel_output_type or ""):
            _dir_dir_text = _pb_d_scene.get("voice_direction", "") or _dir_dir_text

        with dc2:
            if _dir_dir_text:
                st.caption("演出ノート:")
                st.code(_dir_dir_text[:300], language=None)
                if st.button("✏️ プロンプトに追記", key="pb_dir_append_main", use_container_width=True):
                    st.session_state["pb_prompt_text"] += f"\n\n[演出ディレクション]\n{_dir_dir_text}"
                    st.rerun()
            else:
                st.caption("（このシーンの演出ノートはありません）")

    # ── Save as template ───────────────────────────────────────────────────────

    st.divider()
    st.subheader("💾 テンプレートとして保存")
    save_c1, save_c2 = st.columns([3, 1])
    with save_c1:
        tmpl_name = st.text_input(
            "テンプレート名 *",
            key="pb_tmpl_name",
            placeholder="例: 解説動画・明るいオフィス・calm",
        )
    with save_c2:
        st.write("")
        st.write("")
        save_btn = st.button("💾 保存", type="primary", use_container_width=True)

    if save_btn:
        if not tmpl_name.strip():
            st.error("テンプレート名を入力してください")
        else:
            new_tmpl = {
                "name":            tmpl_name.strip(),
                "output_type":     sel_output_type,
                "character_id":    sel_char_id,
                "background_id":   sel_bg_id,
                "mood":            sel_mood,
                "camera":          sel_camera,
                "style":           sel_style,
                "prompt_text":     prompt_text,
                "negative_prompt": negative,
                "notes":           notes_input,
            }
            saved = add_template(new_tmpl)
            st.session_state["pb_selected_id"] = saved["id"]
            st.success(f"テンプレート「{tmpl_name}」を保存しました ✅")
            st.rerun()


# ── Template management (when one is selected) ─────────────────────────────────

selected_id = st.session_state.get("pb_selected_id")
if selected_id:
    # Re-load fresh from disk
    current_tmpl = get_template(selected_id)
    if current_tmpl:
        st.divider()
        st.subheader(f"🗂️ テンプレート管理: {current_tmpl['name']}")

        tm_c1, tm_c2 = st.columns([3, 2])
        with tm_c1:
            st.markdown(f"**ID:** `{current_tmpl['id']}`")
            st.markdown(f"**出力タイプ:** {current_tmpl.get('output_type','')}")
            st.markdown(
                f"**ムード:** {current_tmpl.get('mood','')} | "
                f"**カメラ:** {current_tmpl.get('camera','')} | "
                f"**スタイル:** {current_tmpl.get('style','')}"
            )
            char_id_t = current_tmpl.get("character_id")
            bg_id_t   = current_tmpl.get("background_id")
            char_t    = next((c for c in all_chars if c["id"] == char_id_t), None)
            bg_t      = next((b for b in all_bgs   if b["id"] == bg_id_t),   None)
            st.markdown(
                f"**キャラクター:** {char_t['basic']['display_name'] if char_t else '（なし）'} | "
                f"**背景:** {bg_t['basic']['display_name'] if bg_t else '（なし）'}"
            )
            st.markdown(f"**作成:** {current_tmpl.get('created_at','')[:10]} | "
                        f"**更新:** {current_tmpl.get('updated_at','')[:10]}")

        with tm_c2:
            edit_notes = st.text_area(
                "ノートを編集",
                value=current_tmpl.get("notes", ""),
                height=100,
                key=f"edit_notes_{selected_id}",
            )
            if st.button("📝 ノートを更新", use_container_width=True):
                update_template(selected_id, {"notes": edit_notes})
                st.success("ノートを更新しました")
                st.rerun()

        act_c1, act_c2 = st.columns(2)
        with act_c1:
            if st.button("📋 複製", use_container_width=True):
                new_t = duplicate_template(selected_id)
                if new_t:
                    st.session_state["pb_selected_id"] = new_t["id"]
                    st.session_state["pb_prompt_text"]  = new_t["prompt_text"]
                    st.session_state["pb_negative"]     = new_t.get("negative_prompt", "")
                    st.success(f"複製しました: {new_t['name']}")
                    st.rerun()

        with act_c2:
            with st.expander("⚠️ 削除"):
                confirm_del = st.checkbox(
                    f"「{current_tmpl['name']}」を削除することを確認",
                    key=f"confirm_del_{selected_id}",
                )
                if st.button(
                    "🗑️ 削除する",
                    disabled=not confirm_del,
                    key=f"del_btn_{selected_id}",
                    use_container_width=True,
                ):
                    delete_template(selected_id)
                    st.session_state["pb_selected_id"] = None
                    st.session_state["pb_prompt_text"]  = ""
                    st.session_state["pb_negative"]     = ""
                    st.success("削除しました")
                    st.rerun()
    else:
        # Template was deleted externally
        st.session_state["pb_selected_id"] = None


# ── Usage guide ────────────────────────────────────────────────────────────────

if not prompt_text:
    st.divider()
    st.info(
        "**使い方:**\n\n"
        "1. キャラクター・背景・出力タイプ・ムード・スタイル・カメラを選択\n"
        "2. 「🔧 プロンプトを生成」をクリック\n"
        "3. 生成されたプロンプトをコピーして Nano Banana / Runway で使用\n"
        "4. 「💾 テンプレートとして保存」でよく使う組み合わせを保存\n"
        "5. 左のサイドバーから保存済みテンプレートをすぐに読み込み\n"
        "6. ⚡ 一発生成 ページでテンプレートを選択してAI生成に反映"
    )
