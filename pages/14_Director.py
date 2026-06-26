import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import OPENAI_API_KEY, PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.utils.character_manager import load_characters
from src.utils.background_manager import load_backgrounds
from src.pipeline.script_pipeline import load_episode_data
from src.director.director_schema import (
    CAMERA_ANGLE_OPTIONS,
    CAMERA_MOTION_OPTIONS,
    EMOTION_HINT,
    FRAMING_HINT,
    LIGHTING_HINT,
    PACING_OPTIONS,
    VISUAL_STYLE_OPTIONS,
    make_empty_plan,
    make_empty_scene_direction,
)
from src.director.director_planner import (
    generate_plan_with_ai,
    load_director_plan,
    plan_exists,
    save_director_plan,
)

st.set_page_config(page_title="AI Director", page_icon="🎬", layout="wide")
st.title("🎬 AI Director")
st.caption("エピソードの演出計画を設計・AI生成し、ビジュアルディレクションを管理 | v3.1")

_settings = load_settings()
_ai_cfg   = _settings["ai"]

# ── Shared data ────────────────────────────────────────────────────────────────

_char_data     = load_characters()
_all_chars     = _char_data["characters"]
_char_id_opts  = [None] + [c["id"] for c in _all_chars]
_char_name_map: dict = {None: "（なし）"}
_char_name_map.update({c["id"]: c["basic"]["display_name"] for c in _all_chars})

_bg_data      = load_backgrounds()
_all_bgs      = _bg_data["backgrounds"]
_bg_id_opts   = [None] + [b["id"] for b in _all_bgs]
_bg_name_map: dict = {None: "（なし）"}
_bg_name_map.update({b["id"]: b["basic"]["display_name"] for b in _all_bgs})

_project_dir = PROJECT_ROOT / "project"
_ep_dirs: list[Path] = sorted(
    [d for d in _project_dir.iterdir() if d.is_dir() and (d / "episode.json").exists()],
    key=lambda d: d.name,
) if _project_dir.exists() else []


# ── State helpers ──────────────────────────────────────────────────────────────

def _safe_val(options: list, value, default=None):
    d = default if default is not None else options[0]
    return value if (value in options) else d


def _safe_id(id_opts: list, value):
    return value if value in id_opts else None


def _init_plan_state(ep_id: str, plan: dict) -> None:
    """Copy plan fields into session state widget keys."""
    pfx = f"dir_{ep_id}"
    st.session_state[f"{pfx}_overall_tone"]            = plan.get("overall_tone", "")
    st.session_state[f"{pfx}_target_emotion"]          = plan.get("target_emotion", "")
    st.session_state[f"{pfx}_visual_style"]            = _safe_val(VISUAL_STYLE_OPTIONS, plan.get("visual_style", ""))
    st.session_state[f"{pfx}_pacing"]                  = _safe_val(PACING_OPTIONS, plan.get("pacing", ""))
    st.session_state[f"{pfx}_rec_char_id"]             = _safe_id(_char_id_opts, plan.get("recommended_character_id"))
    st.session_state[f"{pfx}_rec_bg_id"]               = _safe_id(_bg_id_opts, plan.get("recommended_background_id"))
    st.session_state[f"{pfx}_thumbnail_direction"]     = plan.get("thumbnail_direction", "")
    st.session_state[f"{pfx}_bgm_direction"]           = plan.get("bgm_direction", "")
    st.session_state[f"{pfx}_se_direction"]            = plan.get("se_direction", "")
    st.session_state[f"{pfx}_risk_notes"]              = plan.get("risk_notes", "")
    for scene in plan.get("scenes", []):
        n = scene.get("scene_no", 1)
        st.session_state[f"{pfx}_s{n}_scene_goal"]             = scene.get("scene_goal", "")
        st.session_state[f"{pfx}_s{n}_emotion"]                = scene.get("emotion", "")
        st.session_state[f"{pfx}_s{n}_camera_angle"]           = _safe_val(CAMERA_ANGLE_OPTIONS, scene.get("camera_angle", ""))
        st.session_state[f"{pfx}_s{n}_camera_motion"]          = _safe_val(CAMERA_MOTION_OPTIONS, scene.get("camera_motion", ""))
        st.session_state[f"{pfx}_s{n}_framing"]                = scene.get("framing", "")
        st.session_state[f"{pfx}_s{n}_lighting"]               = scene.get("lighting", "")
        st.session_state[f"{pfx}_s{n}_char_id"]                = _safe_id(_char_id_opts, scene.get("character_id"))
        st.session_state[f"{pfx}_s{n}_bg_id"]                  = _safe_id(_bg_id_opts, scene.get("background_id"))
        st.session_state[f"{pfx}_s{n}_image_prompt_direction"] = scene.get("image_prompt_direction", "")
        st.session_state[f"{pfx}_s{n}_video_prompt_direction"] = scene.get("video_prompt_direction", "")
        st.session_state[f"{pfx}_s{n}_voice_direction"]        = scene.get("voice_direction", "")
        st.session_state[f"{pfx}_s{n}_editing_notes"]          = scene.get("editing_notes", "")


def _collect_plan(ep_id: str, base_plan: dict, sections: list) -> dict:
    """Build a plan dict from current widget session state values."""
    pfx    = f"dir_{ep_id}"
    result = dict(base_plan)
    result["overall_tone"]              = st.session_state.get(f"{pfx}_overall_tone", "")
    result["target_emotion"]            = st.session_state.get(f"{pfx}_target_emotion", "")
    result["visual_style"]              = st.session_state.get(f"{pfx}_visual_style", VISUAL_STYLE_OPTIONS[0])
    result["pacing"]                    = st.session_state.get(f"{pfx}_pacing", PACING_OPTIONS[1])
    result["recommended_character_id"]  = st.session_state.get(f"{pfx}_rec_char_id")
    result["recommended_background_id"] = st.session_state.get(f"{pfx}_rec_bg_id")
    result["thumbnail_direction"]       = st.session_state.get(f"{pfx}_thumbnail_direction", "")
    result["bgm_direction"]             = st.session_state.get(f"{pfx}_bgm_direction", "")
    result["se_direction"]              = st.session_state.get(f"{pfx}_se_direction", "")
    result["risk_notes"]                = st.session_state.get(f"{pfx}_risk_notes", "")
    old_scenes = {s["scene_no"]: s for s in base_plan.get("scenes", [])}
    scenes: list[dict] = []
    for i in range(len(sections)):
        n    = i + 1
        base = old_scenes.get(n, make_empty_scene_direction(n))
        scenes.append({
            "scene_no":               n,
            "scene_goal":             st.session_state.get(f"{pfx}_s{n}_scene_goal",             base.get("scene_goal", "")),
            "emotion":                st.session_state.get(f"{pfx}_s{n}_emotion",                base.get("emotion", "")),
            "camera_angle":           st.session_state.get(f"{pfx}_s{n}_camera_angle",           base.get("camera_angle", CAMERA_ANGLE_OPTIONS[0])),
            "camera_motion":          st.session_state.get(f"{pfx}_s{n}_camera_motion",          base.get("camera_motion", CAMERA_MOTION_OPTIONS[0])),
            "framing":                st.session_state.get(f"{pfx}_s{n}_framing",                base.get("framing", "")),
            "lighting":               st.session_state.get(f"{pfx}_s{n}_lighting",               base.get("lighting", "")),
            "character_id":           st.session_state.get(f"{pfx}_s{n}_char_id",                base.get("character_id")),
            "background_id":          st.session_state.get(f"{pfx}_s{n}_bg_id",                  base.get("background_id")),
            "image_prompt_direction": st.session_state.get(f"{pfx}_s{n}_image_prompt_direction", base.get("image_prompt_direction", "")),
            "video_prompt_direction": st.session_state.get(f"{pfx}_s{n}_video_prompt_direction", base.get("video_prompt_direction", "")),
            "voice_direction":        st.session_state.get(f"{pfx}_s{n}_voice_direction",        base.get("voice_direction", "")),
            "editing_notes":          st.session_state.get(f"{pfx}_s{n}_editing_notes",          base.get("editing_notes", "")),
        })
    result["scenes"] = scenes
    return result


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader(f"📁 エピソード ({len(_ep_dirs)})")

    if not _ep_dirs:
        st.caption("エピソードがありません")
    else:
        for _ep_d in _ep_dirs:
            _has_plan = plan_exists(_ep_d)
            _prefix   = "🎬 " if _has_plan else ""
            _is_sel   = st.session_state.get("dir_ep_id") == _ep_d.name
            if st.button(
                f"{_prefix}{_ep_d.name}",
                key=f"dir_sb_{_ep_d.name}",
                use_container_width=True,
                type="primary" if _is_sel else "secondary",
            ):
                st.session_state["dir_ep_id"] = _ep_d.name
                st.rerun()

    st.divider()
    st.caption(f"🤖 `{_ai_cfg['model']}`")
    st.caption(f"OpenAI: {'✅' if OPENAI_API_KEY else '❌ 未設定'}")

# ── No episodes ────────────────────────────────────────────────────────────────

if not _ep_dirs:
    st.info(
        "エピソードがありません。\n\n"
        "⚡ 一発生成 または 🎞️ エピソード管理 でエピソードを作成してください。"
    )
    st.stop()

# ── Episode selection ──────────────────────────────────────────────────────────

ep_names    = [d.name for d in _ep_dirs]
default_ep  = st.session_state.get("dir_ep_id", ep_names[0])
default_idx = ep_names.index(default_ep) if default_ep in ep_names else 0

sel_ep_name = st.selectbox(
    "📁 エピソードを選択",
    ep_names,
    index=default_idx,
    key="dir_ep_sel",
)
st.session_state["dir_ep_id"] = sel_ep_name

episode_dir  = _project_dir / sel_ep_name
episode_data = load_episode_data(episode_dir) or {}
sections     = episode_data.get("sections", [])

# ── Episode switch — load plan and init state ──────────────────────────────────

if st.session_state.get("dir_last_ep_id") != sel_ep_name:
    _disk_plan = load_director_plan(episode_dir) or make_empty_plan(sel_ep_name, episode_data)
    _init_plan_state(sel_ep_name, _disk_plan)
    st.session_state["dir_base_plan"]   = _disk_plan
    st.session_state["dir_last_ep_id"]  = sel_ep_name
    st.rerun()

# ── AI-generated plan signal ───────────────────────────────────────────────────

if "dir_ai_plan" in st.session_state:
    _ai_plan = st.session_state.pop("dir_ai_plan")
    _init_plan_state(sel_ep_name, _ai_plan)
    st.session_state["dir_base_plan"] = _ai_plan
    st.rerun()

# ── Reset signal ───────────────────────────────────────────────────────────────

if st.session_state.pop("dir_reset_flag", False):
    _empty = make_empty_plan(sel_ep_name, episode_data)
    _init_plan_state(sel_ep_name, _empty)
    st.session_state["dir_base_plan"] = _empty
    st.rerun()

base_plan = st.session_state.get("dir_base_plan", make_empty_plan(sel_ep_name, episode_data))
pfx       = f"dir_{sel_ep_name}"

# ── Episode info + action bar ──────────────────────────────────────────────────

ep_title  = episode_data.get("title", "（タイトル未設定）")
ep_scenes = len(sections)
has_plan  = plan_exists(episode_dir)

info_col, badge_col, btn_col = st.columns([4, 1, 3])
with info_col:
    st.subheader(ep_title)
    st.caption(
        f"ID: `{sel_ep_name}` | {ep_scenes} シーン"
        + (" | 🎬 演出計画あり" if has_plan else " | 演出計画なし")
    )
with badge_col:
    if has_plan:
        plan_mtime = (episode_dir / "director_plan.json").stat().st_mtime
        from datetime import datetime as _dt
        st.caption(f"更新: {_dt.fromtimestamp(plan_mtime).strftime('%m/%d %H:%M')}")
with btn_col:
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        if ac1.button("💾 保存", type="primary", use_container_width=True, key="dir_save_top"):
            current = _collect_plan(sel_ep_name, base_plan, sections)
            save_director_plan(episode_dir, current)
            st.session_state["dir_base_plan"] = current
            st.success("保存しました ✅")
            st.rerun()
    with ac2:
        if ac2.button("📋 複製", use_container_width=True, key="dir_dup_top"):
            if has_plan:
                import copy as _copy
                _dup = _copy.deepcopy(base_plan)
                _dup["title"] = _dup.get("title", "") + " (コピー)"
                _init_plan_state(sel_ep_name, _dup)
                st.session_state["dir_base_plan"] = _dup
                st.info("複製しました（まだ保存されていません）")
                st.rerun()
    with ac3:
        if ac3.button("⚠️ リセット", use_container_width=True, key="dir_reset_btn"):
            st.session_state["dir_show_reset_confirm"] = True

if st.session_state.pop("dir_show_reset_confirm", False):
    if st.checkbox("演出計画を空にリセットすることを確認", key="dir_reset_confirm_chk"):
        if st.button("🗑️ リセット実行", key="dir_reset_exec", type="primary"):
            st.session_state["dir_reset_flag"] = True
            st.rerun()

st.divider()

# ── Main layout — two columns ──────────────────────────────────────────────────

left_col, right_col = st.columns([3, 2])

# ════════════════════════════════════════════════════════════════
# LEFT: Overall direction + Scene editor + Global direction
# ════════════════════════════════════════════════════════════════

with left_col:

    # ── Overall direction ──────────────────────────────────────────────────────

    st.subheader("🎨 全体演出設定")

    oc1, oc2 = st.columns(2)
    with oc1:
        st.text_input(
            "全体トーン",
            key=f"{pfx}_overall_tone",
            placeholder="例: 明るくポジティブ、重厚でシリアス、温かみのある教育的",
        )
        st.text_input(
            "目標感情",
            key=f"{pfx}_target_emotion",
            placeholder=EMOTION_HINT,
        )
    with oc2:
        # Validate before rendering (episode switch sets valid values via _init_plan_state)
        st.selectbox(
            "ビジュアルスタイル",
            VISUAL_STYLE_OPTIONS,
            key=f"{pfx}_visual_style",
        )
        st.selectbox(
            "ペーシング",
            PACING_OPTIONS,
            key=f"{pfx}_pacing",
        )

    oc3, oc4 = st.columns(2)
    with oc3:
        _rc_idx = _char_id_opts.index(st.session_state.get(f"{pfx}_rec_char_id")) \
            if st.session_state.get(f"{pfx}_rec_char_id") in _char_id_opts else 0
        st.selectbox(
            "推奨キャラクター",
            _char_id_opts,
            format_func=lambda x: _char_name_map.get(x, "不明"),
            index=_rc_idx,
            key=f"{pfx}_rec_char_id",
        )
    with oc4:
        _rb_idx = _bg_id_opts.index(st.session_state.get(f"{pfx}_rec_bg_id")) \
            if st.session_state.get(f"{pfx}_rec_bg_id") in _bg_id_opts else 0
        st.selectbox(
            "推奨背景",
            _bg_id_opts,
            format_func=lambda x: _bg_name_map.get(x, "不明"),
            index=_rb_idx,
            key=f"{pfx}_rec_bg_id",
        )

    st.divider()

    # ── Scene editor ───────────────────────────────────────────────────────────

    st.subheader(f"🎬 シーン別演出 ({ep_scenes} シーン)")

    if not sections:
        st.info("エピソードにシーンがありません。エピソードを生成してからここで演出を設定してください。")
    else:
        for i, section in enumerate(sections):
            n        = i + 1
            scene_id = section.get("id", n)
            title    = section.get("title", f"シーン {n}")
            goal_val = st.session_state.get(f"{pfx}_s{n}_scene_goal", "")
            emo_val  = st.session_state.get(f"{pfx}_s{n}_emotion", "")
            header   = f"**シーン {n}**: {title}"
            if goal_val:
                header += f"  —  目標: {goal_val[:30]}"
            if emo_val:
                header += f"  |  感情: {emo_val}"

            with st.expander(header, expanded=(n == 1)):
                # Scene narration hint
                narration = section.get("narration_text", "")
                if narration:
                    st.caption(f"📝 ナレーション: {narration[:120]}{'…' if len(narration) > 120 else ''}")

                s1c1, s1c2 = st.columns([3, 2])
                with s1c1:
                    st.text_input(
                        "シーンゴール",
                        key=f"{pfx}_s{n}_scene_goal",
                        placeholder="このシーンで視聴者に伝えたいこと・達成したい演出",
                    )
                    st.text_input(
                        "感情・トーン",
                        key=f"{pfx}_s{n}_emotion",
                        placeholder=EMOTION_HINT,
                    )
                with s1c2:
                    _ca_val = st.session_state.get(f"{pfx}_s{n}_camera_angle", CAMERA_ANGLE_OPTIONS[0])
                    _ca_idx = _ca_val if _ca_val not in CAMERA_ANGLE_OPTIONS else CAMERA_ANGLE_OPTIONS.index(_ca_val)
                    if isinstance(_ca_idx, str):
                        _ca_idx = 0
                    st.selectbox(
                        "カメラアングル",
                        CAMERA_ANGLE_OPTIONS,
                        index=_ca_idx,
                        key=f"{pfx}_s{n}_camera_angle",
                    )
                    _cm_val = st.session_state.get(f"{pfx}_s{n}_camera_motion", CAMERA_MOTION_OPTIONS[0])
                    _cm_idx = CAMERA_MOTION_OPTIONS.index(_cm_val) if _cm_val in CAMERA_MOTION_OPTIONS else 0
                    st.selectbox(
                        "カメラモーション",
                        CAMERA_MOTION_OPTIONS,
                        index=_cm_idx,
                        key=f"{pfx}_s{n}_camera_motion",
                    )

                s2c1, s2c2, s2c3 = st.columns(3)
                with s2c1:
                    st.text_input("フレーミング", key=f"{pfx}_s{n}_framing",  placeholder=FRAMING_HINT)
                with s2c2:
                    st.text_input("ライティング", key=f"{pfx}_s{n}_lighting", placeholder=LIGHTING_HINT)
                with s2c3:
                    _sc_idx = _char_id_opts.index(st.session_state.get(f"{pfx}_s{n}_char_id")) \
                        if st.session_state.get(f"{pfx}_s{n}_char_id") in _char_id_opts else 0
                    st.selectbox(
                        "キャラクター",
                        _char_id_opts,
                        format_func=lambda x: _char_name_map.get(x, "不明"),
                        index=_sc_idx,
                        key=f"{pfx}_s{n}_char_id",
                    )

                s3c1, s3c2 = st.columns(2)
                with s3c1:
                    _sb_idx = _bg_id_opts.index(st.session_state.get(f"{pfx}_s{n}_bg_id")) \
                        if st.session_state.get(f"{pfx}_s{n}_bg_id") in _bg_id_opts else 0
                    st.selectbox(
                        "背景",
                        _bg_id_opts,
                        format_func=lambda x: _bg_name_map.get(x, "不明"),
                        index=_sb_idx,
                        key=f"{pfx}_s{n}_bg_id",
                    )
                with s3c2:
                    st.text_input(
                        "ボイスディレクション",
                        key=f"{pfx}_s{n}_voice_direction",
                        placeholder="話速、感情、強調箇所など",
                    )

                st.text_area(
                    "🖼️ 画像プロンプト演出ノート",
                    key=f"{pfx}_s{n}_image_prompt_direction",
                    height=80,
                    placeholder="Nano Banana / Midjourney 用のビジュアル方向性",
                )
                st.text_area(
                    "🎬 動画プロンプト演出ノート",
                    key=f"{pfx}_s{n}_video_prompt_direction",
                    height=80,
                    placeholder="Runway Gen-3 Alpha 用のモーション・雰囲気方向性",
                )
                st.text_input(
                    "編集ノート",
                    key=f"{pfx}_s{n}_editing_notes",
                    placeholder="トランジション、カット、テロップなど編集時の指示",
                )

    st.divider()

    # ── Global direction ───────────────────────────────────────────────────────

    st.subheader("🌐 グローバル演出設定")

    gc1, gc2 = st.columns(2)
    with gc1:
        st.text_area(
            "🖼️ サムネイル演出",
            key=f"{pfx}_thumbnail_direction",
            height=80,
            placeholder="サムネイル画像のビジュアル方向性・キャッチコピー候補",
        )
        st.text_area(
            "🎵 BGM演出",
            key=f"{pfx}_bgm_direction",
            height=80,
            placeholder="BGMのムード・ジャンル・テンポ",
        )
    with gc2:
        st.text_area(
            "🔊 SE演出",
            key=f"{pfx}_se_direction",
            height=80,
            placeholder="効果音の種類・タイミング",
        )
        st.text_area(
            "⚠️ リスクノート",
            key=f"{pfx}_risk_notes",
            height=80,
            placeholder="制作上の注意点・懸念事項・代替案",
        )

    # Save button (bottom)
    if st.button("💾 演出計画を保存", type="primary", use_container_width=True, key="dir_save_bottom"):
        current = _collect_plan(sel_ep_name, base_plan, sections)
        save_director_plan(episode_dir, current)
        st.session_state["dir_base_plan"] = current
        st.success("演出計画を保存しました ✅")
        st.rerun()


# ════════════════════════════════════════════════════════════════
# RIGHT: AI generation + Plan summary
# ════════════════════════════════════════════════════════════════

with right_col:

    # ── AI Assisted Director ───────────────────────────────────────────────────

    st.subheader("🤖 AI 演出生成")

    if not OPENAI_API_KEY:
        st.warning("OpenAI API キーが未設定です。AI演出生成を使用するには `.env` に `OPENAI_API_KEY` を設定してください。")
    else:
        with st.expander("⚙️ AI生成設定", expanded=not has_plan):
            ai_tone  = st.text_input(
                "全体トーン（AIへの指示）",
                placeholder="例: 明るくポジティブ、エモーショナルな感動系",
                key="dir_ai_tone",
            )
            ai_emotion = st.text_input(
                "目標感情",
                placeholder=EMOTION_HINT,
                key="dir_ai_emotion",
            )
            ai_style_idx = VISUAL_STYLE_OPTIONS.index(
                st.session_state.get("dir_ai_style", VISUAL_STYLE_OPTIONS[0])
            ) if st.session_state.get("dir_ai_style") in VISUAL_STYLE_OPTIONS else 0
            ai_style = st.selectbox(
                "ビジュアルスタイル",
                VISUAL_STYLE_OPTIONS,
                index=ai_style_idx,
                key="dir_ai_style",
            )
            ai_pacing_idx = PACING_OPTIONS.index(
                st.session_state.get("dir_ai_pacing", PACING_OPTIONS[1])
            ) if st.session_state.get("dir_ai_pacing") in PACING_OPTIONS else 1
            ai_pacing = st.selectbox(
                "ペーシング",
                PACING_OPTIONS,
                index=ai_pacing_idx,
                key="dir_ai_pacing",
            )

            ai_char_idx = _char_id_opts.index(st.session_state.get("dir_ai_char_id")) \
                if st.session_state.get("dir_ai_char_id") in _char_id_opts else 0
            ai_char_id = st.selectbox(
                "キャラクター（AI参考）",
                _char_id_opts,
                format_func=lambda x: _char_name_map.get(x, "不明"),
                index=ai_char_idx,
                key="dir_ai_char_id",
            )
            ai_bg_idx = _bg_id_opts.index(st.session_state.get("dir_ai_bg_id")) \
                if st.session_state.get("dir_ai_bg_id") in _bg_id_opts else 0
            ai_bg_id = st.selectbox(
                "背景（AI参考）",
                _bg_id_opts,
                format_func=lambda x: _bg_name_map.get(x, "不明"),
                index=ai_bg_idx,
                key="dir_ai_bg_id",
            )

            if not sections:
                st.warning("エピソードにシーンがないためAI生成できません")
            else:
                if st.button(
                    "🤖 AI演出計画を生成",
                    type="primary",
                    use_container_width=True,
                    key="dir_ai_gen_btn",
                ):
                    _ai_char = next((c for c in _all_chars if c["id"] == ai_char_id), None)
                    _ai_bg   = next((b for b in _all_bgs   if b["id"] == ai_bg_id),   None)
                    with st.spinner("OpenAI で演出計画を生成中..."):
                        try:
                            _gen_plan = generate_plan_with_ai(
                                episode_dir=episode_dir,
                                episode_data=episode_data,
                                character=_ai_char,
                                background=_ai_bg,
                                overall_tone=ai_tone,
                                visual_style=ai_style,
                                pacing=ai_pacing,
                                target_emotion=ai_emotion,
                            )
                            st.session_state["dir_ai_plan"] = _gen_plan
                            st.success("AI演出計画を生成しました ✅ — 確認して保存してください")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"生成エラー: {exc}")
                            st.exception(exc)

    st.divider()

    # ── Plan summary ───────────────────────────────────────────────────────────

    st.subheader("📋 演出計画サマリー")

    _current_summary = _collect_plan(sel_ep_name, base_plan, sections)
    tone_v  = st.session_state.get(f"{pfx}_overall_tone", "")
    emo_v   = st.session_state.get(f"{pfx}_target_emotion", "")
    style_v = st.session_state.get(f"{pfx}_visual_style", "")
    pace_v  = st.session_state.get(f"{pfx}_pacing", "")

    sc1, sc2 = st.columns(2)
    sc1.metric("スタイル", style_v or "—")
    sc2.metric("ペーシング", pace_v or "—")
    if tone_v:
        st.caption(f"トーン: {tone_v}")
    if emo_v:
        st.caption(f"感情: {emo_v}")

    _rec_char_id = st.session_state.get(f"{pfx}_rec_char_id")
    _rec_bg_id   = st.session_state.get(f"{pfx}_rec_bg_id")
    if _rec_char_id:
        st.caption(f"推奨キャラクター: {_char_name_map.get(_rec_char_id, '—')}")
    if _rec_bg_id:
        st.caption(f"推奨背景: {_bg_name_map.get(_rec_bg_id, '—')}")

    if sections:
        st.divider()
        st.caption("**シーンサマリー**")
        for i, section in enumerate(sections):
            n       = i + 1
            s_goal  = st.session_state.get(f"{pfx}_s{n}_scene_goal", "")
            s_emo   = st.session_state.get(f"{pfx}_s{n}_emotion", "")
            s_cam   = st.session_state.get(f"{pfx}_s{n}_camera_angle", "")
            s_title = section.get("title", f"シーン {n}")
            st.caption(
                f"**S{n}** {s_title[:20]}"
                + (f" | {s_emo}" if s_emo else "")
                + (f" | {s_cam}" if s_cam else "")
                + (f" | {s_goal[:25]}…" if len(s_goal) > 25 else (f" | {s_goal}" if s_goal else ""))
            )

    st.divider()

    # ── Thumbnail + BGM/SE summary ─────────────────────────────────────────────

    thumb_v = st.session_state.get(f"{pfx}_thumbnail_direction", "")
    bgm_v   = st.session_state.get(f"{pfx}_bgm_direction", "")
    se_v    = st.session_state.get(f"{pfx}_se_direction", "")
    risk_v  = st.session_state.get(f"{pfx}_risk_notes", "")

    if any([thumb_v, bgm_v, se_v, risk_v]):
        with st.expander("📄 グローバル演出メモ"):
            if thumb_v:
                st.caption(f"🖼️ サムネイル: {thumb_v[:200]}")
            if bgm_v:
                st.caption(f"🎵 BGM: {bgm_v[:200]}")
            if se_v:
                st.caption(f"🔊 SE: {se_v[:200]}")
            if risk_v:
                st.caption(f"⚠️ リスク: {risk_v[:200]}")

    # ── JSON export ────────────────────────────────────────────────────────────

    st.divider()
    if has_plan:
        _plan_json = (episode_dir / "director_plan.json").read_text(encoding="utf-8")
        with st.expander("📂 director_plan.json"):
            st.download_button(
                "⬇️ ダウンロード",
                data=_plan_json,
                file_name="director_plan.json",
                mime="application/json",
                key="dl_dir_plan",
                use_container_width=True,
            )
            st.code(_plan_json[:3000] + ("…" if len(_plan_json) > 3000 else ""), language="json")
