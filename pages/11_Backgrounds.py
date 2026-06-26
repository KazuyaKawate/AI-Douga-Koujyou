import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.utils.background_manager import (
    BACKGROUNDS_PATH,
    ANGLE_OPTIONS,
    CATEGORY_OPTIONS,
    MOTION_OPTIONS,
    TIME_OPTIONS,
    add_background,
    background_to_prompt_snippet,
    delete_background,
    duplicate_background,
    get_background,
    load_backgrounds,
    make_empty_background,
    preview_prompt,
    set_default_background,
    update_background,
)

st.set_page_config(page_title="背景・シーン管理", page_icon="🏞️", layout="wide")
st.title("🏞️ 背景・シーン管理")
st.caption("ロケーション・カメラ設定・シーンテンプレートを管理します | v2.8")

_settings = load_settings()

# Session state
if "selected_bg_id" not in st.session_state:
    st.session_state.selected_bg_id = None

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    # ── New background ─────────────────────────────────────────────────────────
    st.subheader("➕ 新規作成")
    new_name = st.text_input("背景名 *", key="new_bg_name", placeholder="例: 明るいオフィス")
    new_cat  = st.selectbox("カテゴリ", CATEGORY_OPTIONS, key="new_bg_cat")
    if st.button("✨ 作成", type="primary", use_container_width=True):
        if not new_name.strip():
            st.error("背景名を入力してください")
        else:
            blank = make_empty_background(new_name.strip(), new_cat)
            saved = add_background(blank)
            st.session_state.selected_bg_id = saved["id"]
            for k in ("new_bg_name",):
                st.session_state.pop(k, None)
            st.rerun()

    st.divider()

    # ── Background list ────────────────────────────────────────────────────────
    bg_data    = load_backgrounds()
    bgs        = bg_data["backgrounds"]
    default_id = bg_data.get("default_background_id")

    st.subheader(f"背景一覧  ({len(bgs)})")
    if not bgs:
        st.info("まだ背景がありません")
    else:
        for bg in bgs:
            is_def = bg["id"] == default_id
            is_sel = bg["id"] == st.session_state.selected_bg_id
            label  = f"{'⭐ ' if is_def else ''}{bg['basic']['display_name']}"
            cat    = bg["basic"].get("category", "")
            if cat:
                label += f"  [{cat}]"
            if st.button(
                label,
                key=f"sel_{bg['id']}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state.selected_bg_id = bg["id"]
                st.rerun()

    st.divider()

    # ── Default background ─────────────────────────────────────────────────────
    st.subheader("⭐ デフォルト背景")
    st.caption("一発生成で自動的に使用されます")

    if bgs:
        id_options = [None] + [b["id"] for b in bgs]
        name_map   = {None: "（なし）"}
        name_map.update({b["id"]: b["basic"]["display_name"] for b in bgs})
        def_idx    = id_options.index(default_id) if default_id in id_options else 0
        new_default = st.selectbox(
            "デフォルト",
            id_options,
            format_func=lambda x: name_map.get(x, "不明"),
            index=def_idx,
            key="default_bg_sel",
            label_visibility="collapsed",
        )
        if st.button("⭐ 設定を保存", use_container_width=True):
            set_default_background(new_default)
            st.success("デフォルトを更新しました")
            st.rerun()
    else:
        st.caption("背景がありません")

    st.divider()
    st.caption(f"⚙️ `{_settings['ai']['model']}` | `{BACKGROUNDS_PATH.name}`")


# ── Re-load after possible sidebar mutations ───────────────────────────────────

bg_data    = load_backgrounds()
bgs        = bg_data["backgrounds"]
default_id = bg_data.get("default_background_id")

# ── Empty state ────────────────────────────────────────────────────────────────

if not bgs:
    st.info(
        "まだ背景がありません。\n\n"
        "左のサイドバーの「新規作成」から背景を追加してください。"
    )
    st.stop()


# ── List overview (no background selected) ────────────────────────────────────

if not st.session_state.selected_bg_id:
    st.info("👈 左のサイドバーから背景を選択してください")
    st.subheader(f"背景一覧 ({len(bgs)} 件)")

    for bg in bgs:
        is_def = bg["id"] == default_id
        badge  = "  ⭐ デフォルト" if is_def else ""
        with st.expander(
            f"{'★ ' if is_def else ''}**{bg['basic']['display_name']}**"
            f"  [{bg['basic'].get('category','')}]{badge}"
        ):
            c1, c2 = st.columns([1, 1])
            with c1:
                v = bg["visual"]
                cam = bg["camera"]
                st.markdown(f"**ロケーション:** {v.get('location_type') or '-'}")
                st.markdown(f"**時間帯:** {v.get('time_of_day') or '-'} | **照明:** {v.get('lighting') or '-'}")
                st.markdown(f"**雰囲気:** {v.get('atmosphere') or '-'}")
                st.markdown(f"**カメラ:** {cam.get('default_camera_angle') or '-'} / {cam.get('default_motion') or '-'}")
                if bg["basic"].get("description"):
                    st.caption(bg["basic"]["description"])
            with c2:
                img_base = bg["prompt"].get("image_prompt_base", "")
                if img_base:
                    st.caption("画像プロンプトベース:")
                    st.code(img_base[:200], language=None)
                layout = bg["assets"].get("layout_image")
                if layout:
                    full = PROJECT_ROOT / layout
                    if full.exists():
                        st.image(str(full), width=160)
            if st.button("✏️ 編集する", key=f"edit_{bg['id']}", use_container_width=True):
                st.session_state.selected_bg_id = bg["id"]
                st.rerun()
    st.stop()


# ── Background editor ──────────────────────────────────────────────────────────

bg_data    = load_backgrounds()
bgs        = bg_data["backgrounds"]
default_id = bg_data.get("default_background_id")
bg         = next((b for b in bgs if b["id"] == st.session_state.selected_bg_id), None)

if not bg:
    st.warning("背景が見つかりません（削除された可能性があります）")
    st.session_state.selected_bg_id = None
    st.rerun()

bid    = bg["id"]
is_def = bid == default_id

# Header
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.subheader(
        f"{'⭐ ' if is_def else ''}✏️ {bg['basic']['display_name']}"
        f"  —  {bg['basic'].get('category','')}"
    )
with hc2:
    if is_def:
        st.success("⭐ デフォルト")
    st.caption(f"ID: `{bid}`")
    st.caption(f"更新: {bg.get('updated_at','')[:10]}")

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_basic, tab_visual, tab_camera, tab_prompt, tab_assets = st.tabs([
    "📝 基本情報", "🎨 ビジュアル", "🎥 カメラ", "✍️ プロンプト", "📁 アセット",
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — Basic
# ════════════════════════════════════════════════════════════════
with tab_basic:
    c1, c2 = st.columns(2)
    with c1:
        v_name = st.text_input(
            "背景名 *",
            value=bg["basic"].get("display_name", ""),
            key=f"{bid}_name",
        )
        _cat    = bg["basic"].get("category", "インドア")
        _catidx = CATEGORY_OPTIONS.index(_cat) if _cat in CATEGORY_OPTIONS else 0
        v_category = st.selectbox(
            "カテゴリ",
            CATEGORY_OPTIONS,
            index=_catidx,
            key=f"{bid}_category",
        )
    with c2:
        v_description = st.text_area(
            "説明",
            value=bg["basic"].get("description", ""),
            height=120,
            key=f"{bid}_description",
            placeholder="例: 清潔感のある現代的なオフィス。大きな窓から自然光が差し込む。",
        )

# ════════════════════════════════════════════════════════════════
# TAB 2 — Visual
# ════════════════════════════════════════════════════════════════
with tab_visual:
    c1, c2 = st.columns(2)
    with c1:
        v_location_type = st.text_input(
            "ロケーションタイプ",
            value=bg["visual"].get("location_type", ""),
            key=f"{bid}_location_type",
            placeholder="例: モダンオフィス, 公園, スタジオ, カフェ",
        )
        _tod    = bg["visual"].get("time_of_day", "昼")
        _todidx = TIME_OPTIONS.index(_tod) if _tod in TIME_OPTIONS else 0
        v_time_of_day = st.selectbox(
            "時間帯",
            TIME_OPTIONS,
            index=_todidx,
            key=f"{bid}_time_of_day",
        )
        v_lighting = st.text_input(
            "照明",
            value=bg["visual"].get("lighting", ""),
            key=f"{bid}_lighting",
            placeholder="例: 自然光, ソフトボックス, 間接照明, 劇的なサイドライト",
        )
    with c2:
        v_color_tone = st.text_input(
            "カラートーン",
            value=bg["visual"].get("color_tone", ""),
            key=f"{bid}_color_tone",
            placeholder="例: ウォームベージュ, クールブルー, モノクロ, パステル",
        )
        v_props = st.text_input(
            "小道具・装飾",
            value=bg["visual"].get("props", ""),
            key=f"{bid}_props",
            placeholder="例: 観葉植物, ホワイトボード, 本棚, コーヒーカップ",
        )
        v_atmosphere = st.text_area(
            "雰囲気",
            value=bg["visual"].get("atmosphere", ""),
            height=80,
            key=f"{bid}_atmosphere",
            placeholder="例: プロフェッショナルで清潔感があり、集中できる空間",
        )

    st.divider()
    st.caption("**ビジュアルプレビュー（画像プロンプト向け）**")
    _tmp_vis = {
        "visual": {
            "location_type": st.session_state.get(f"{bid}_location_type", bg["visual"].get("location_type", "")),
            "lighting":      st.session_state.get(f"{bid}_lighting",      bg["visual"].get("lighting", "")),
            "color_tone":    st.session_state.get(f"{bid}_color_tone",    bg["visual"].get("color_tone", "")),
            "atmosphere":    st.session_state.get(f"{bid}_atmosphere",    bg["visual"].get("atmosphere", "")),
        },
        "camera": bg["camera"],
        "prompt": bg["prompt"],
    }
    st.code(preview_prompt(_tmp_vis, "image") or "（未入力）", language=None)

# ════════════════════════════════════════════════════════════════
# TAB 3 — Camera
# ════════════════════════════════════════════════════════════════
with tab_camera:
    c1, c2 = st.columns(2)
    with c1:
        _ang    = bg["camera"].get("default_camera_angle", "正面")
        _angidx = ANGLE_OPTIONS.index(_ang) if _ang in ANGLE_OPTIONS else 0
        v_camera_angle = st.selectbox(
            "デフォルトカメラアングル",
            ANGLE_OPTIONS,
            index=_angidx,
            key=f"{bid}_camera_angle",
        )
        v_lens = st.text_input(
            "レンズ",
            value=bg["camera"].get("default_lens", ""),
            key=f"{bid}_lens",
            placeholder="例: 50mm標準, 広角24mm, 望遠85mm, シネマレンズ",
        )
    with c2:
        _mot    = bg["camera"].get("default_motion", "静止")
        _motidx = MOTION_OPTIONS.index(_mot) if _mot in MOTION_OPTIONS else 0
        v_motion = st.selectbox(
            "デフォルトカメラモーション",
            MOTION_OPTIONS,
            index=_motidx,
            key=f"{bid}_motion",
        )
        v_framing = st.text_input(
            "フレーミング",
            value=bg["camera"].get("framing", ""),
            key=f"{bid}_framing",
            placeholder="例: バストショット, 全身, クローズアップ, 2/3ショット",
        )

    st.divider()
    st.caption("**動画プロンプトプレビュー（カメラ設定）**")
    _tmp_cam = {
        "visual": bg["visual"],
        "camera": {
            "default_motion":       st.session_state.get(f"{bid}_motion",       bg["camera"].get("default_motion", "")),
            "default_camera_angle": st.session_state.get(f"{bid}_camera_angle", bg["camera"].get("default_camera_angle", "")),
        },
        "prompt": bg["prompt"],
    }
    st.code(preview_prompt(_tmp_cam, "video") or "（未入力）", language=None)

# ════════════════════════════════════════════════════════════════
# TAB 4 — Prompts
# ════════════════════════════════════════════════════════════════
with tab_prompt:
    v_image_prompt_base = st.text_area(
        "画像プロンプトベース",
        value=bg["prompt"].get("image_prompt_base", ""),
        height=90,
        key=f"{bid}_img_base",
        help="各シーンの画像プロンプトに付加される固定テキスト（英語推奨）",
        placeholder="例: modern office interior, large windows, natural daylight, minimalist design, 8k, photorealistic",
    )
    v_video_prompt_base = st.text_area(
        "動画プロンプトベース",
        value=bg["prompt"].get("video_prompt_base", ""),
        height=90,
        key=f"{bid}_vid_base",
        help="各シーンの動画プロンプトに付加される固定テキスト（英語推奨）",
        placeholder="例: steady camera, smooth lighting transition, shallow depth of field, professional broadcast quality",
    )
    v_negative_prompt = st.text_area(
        "ネガティブプロンプト",
        value=bg["prompt"].get("negative_prompt", ""),
        height=70,
        key=f"{bid}_neg",
        help="画像・動画生成時に除外したい要素（英語推奨）",
        placeholder="例: blurry, distorted, low quality, watermark, cartoon, anime",
    )
    v_style_notes = st.text_area(
        "スタイルノート",
        value=bg["prompt"].get("style_notes", ""),
        height=70,
        key=f"{bid}_style_notes",
        help="AIへの補足指示（日本語可）",
        placeholder="例: 全シーンを通じて同じ部屋の一貫した外観を維持すること。照明の色温度は3200K統一。",
    )

    st.divider()
    st.subheader("🔍 AIプロンプトプレビュー")
    st.caption("一発生成でこの背景が選択されたときにAIに渡されるテキスト（保存後に更新）")
    st.code(background_to_prompt_snippet(bg), language=None)

# ════════════════════════════════════════════════════════════════
# TAB 5 — Assets
# ════════════════════════════════════════════════════════════════
with tab_assets:
    assets    = bg.get("assets", {"reference_images": [], "layout_image": None, "sample_video": None})
    assets_dir = PROJECT_ROOT / "assets" / "backgrounds" / bid

    # ── Reference images ───────────────────────────────────────
    st.subheader("🖼️ リファレンス画像")
    ref_images = assets.get("reference_images") or []

    if ref_images:
        ncols = min(len(ref_images), 5)
        ref_cols = st.columns(ncols)
        for i, (col, rp) in enumerate(zip(ref_cols, ref_images)):
            rp_full = PROJECT_ROOT / rp
            if rp_full.exists():
                col.image(str(rp_full), width=130, caption=Path(rp).stem)
            else:
                col.warning("不明")
            if col.button("🗑️", key=f"del_ref_{bid}_{i}"):
                new_list = [r for j, r in enumerate(ref_images) if j != i]
                update_background(bid, {"assets": {"reference_images": new_list}})
                st.rerun()
    else:
        st.caption("リファレンス画像がありません")

    up_refs = st.file_uploader(
        "リファレンス画像を追加（複数可）",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key=f"up_refs_{bid}",
    )
    if up_refs:
        assets_dir.mkdir(parents=True, exist_ok=True)
        new_paths = list(ref_images)
        for f in up_refs:
            dest = assets_dir / f"ref_{len(new_paths):02d}_{f.name}"
            dest.write_bytes(f.getvalue())
            rel = str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if rel not in new_paths:
                new_paths.append(rel)
        update_background(bid, {"assets": {"reference_images": new_paths}})
        st.success(f"{len(up_refs)} 件のリファレンス画像を保存しました ✅")
        st.rerun()

    st.divider()

    # ── Layout image ───────────────────────────────────────────
    st.subheader("📐 レイアウト画像")
    lc1, lc2 = st.columns([1, 2])
    with lc1:
        layout_rel = assets.get("layout_image")
        if layout_rel:
            l_full = PROJECT_ROOT / layout_rel
            if l_full.exists():
                st.image(str(l_full), width=200)
            else:
                st.warning("画像が見つかりません")
        else:
            st.caption("未設定")
    with lc2:
        up_layout = st.file_uploader(
            "レイアウト画像をアップロード",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"up_layout_{bid}",
        )
        if up_layout:
            assets_dir.mkdir(parents=True, exist_ok=True)
            dest = assets_dir / f"layout{Path(up_layout.name).suffix}"
            dest.write_bytes(up_layout.getvalue())
            rel = str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/")
            update_background(bid, {"assets": {"layout_image": rel}})
            st.success("レイアウト画像を保存しました ✅")
            st.rerun()
        if layout_rel:
            if st.button("🗑️ レイアウト画像を削除", key=f"del_layout_{bid}"):
                update_background(bid, {"assets": {"layout_image": None}})
                st.rerun()

    st.divider()

    # ── Sample video ───────────────────────────────────────────
    st.subheader("🎬 サンプル動画")
    video_rel = assets.get("sample_video")
    if video_rel:
        v_full = PROJECT_ROOT / video_rel
        if v_full.exists():
            st.video(v_full.read_bytes())
            st.caption(Path(video_rel).name)
        else:
            st.warning("動画ファイルが見つかりません")
        if st.button("🗑️ サンプル動画を削除", key=f"del_video_{bid}"):
            update_background(bid, {"assets": {"sample_video": None}})
            st.rerun()
    else:
        st.caption("サンプル動画がありません")

    up_video = st.file_uploader(
        "サンプル動画をアップロード",
        type=["mp4", "mov", "webm"],
        key=f"up_video_{bid}",
    )
    if up_video:
        assets_dir.mkdir(parents=True, exist_ok=True)
        dest = assets_dir / f"sample{Path(up_video.name).suffix}"
        dest.write_bytes(up_video.getvalue())
        rel = str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/")
        update_background(bid, {"assets": {"sample_video": rel}})
        st.success("サンプル動画を保存しました ✅")
        st.rerun()

# ── Action buttons ─────────────────────────────────────────────────────────────

st.divider()
btn_save, btn_dup, btn_gap = st.columns([3, 1, 2])

if btn_save.button("💾 変更を保存", type="primary", use_container_width=True):
    updates = {
        "basic": {
            "display_name": v_name,
            "category":     v_category,
            "description":  v_description,
        },
        "visual": {
            "location_type": v_location_type,
            "time_of_day":   v_time_of_day,
            "lighting":      v_lighting,
            "color_tone":    v_color_tone,
            "props":         v_props,
            "atmosphere":    v_atmosphere,
        },
        "camera": {
            "default_camera_angle": v_camera_angle,
            "default_lens":         v_lens,
            "default_motion":       v_motion,
            "framing":              v_framing,
        },
        "prompt": {
            "image_prompt_base": v_image_prompt_base,
            "video_prompt_base": v_video_prompt_base,
            "negative_prompt":   v_negative_prompt,
            "style_notes":       v_style_notes,
        },
    }
    update_background(bid, updates)
    st.success("保存しました ✅")
    st.rerun()

if btn_dup.button("📋 複製", use_container_width=True):
    new_bg = duplicate_background(bid)
    if new_bg:
        st.session_state.selected_bg_id = new_bg["id"]
        st.success(f"複製しました: {new_bg['basic']['display_name']}")
        st.rerun()

with st.expander("⚠️ 危険な操作"):
    confirm_del = st.checkbox(
        f"**{bg['basic']['display_name']}** を削除することを確認",
        key=f"confirm_del_{bid}",
    )
    if st.button(
        "🗑️ 削除する",
        disabled=not confirm_del,
        key=f"del_btn_{bid}",
        use_container_width=True,
    ):
        delete_background(bid)
        st.session_state.selected_bg_id = None
        st.success("削除しました")
        st.rerun()
