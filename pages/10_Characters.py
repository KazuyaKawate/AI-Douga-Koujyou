import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.utils.character_manager import (
    CHARACTERS_PATH,
    add_character,
    character_to_prompt_snippet,
    delete_character,
    duplicate_character,
    edit_character,
    get_character,
    load_characters,
    make_empty_character,
    preview_prompt,
    set_default_character,
)

st.set_page_config(page_title="キャラクター管理", page_icon="🧑", layout="wide")
st.title("🧑 キャラクター管理")
st.caption("動画に登場するキャラクターを作成・管理します | v2.7")

GENDER_OPTIONS = ["female", "male", "other"]
GENDER_LABELS  = {"female": "女性", "male": "男性", "other": "その他"}

_settings = load_settings()

# Session state
if "selected_char_id" not in st.session_state:
    st.session_state.selected_char_id = None

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    # ── New character ──────────────────────────────────────────────────────────
    st.subheader("➕ 新規作成")
    new_name = st.text_input("表示名 *", key="new_char_name", placeholder="例: 花子")
    new_role = st.text_input("役割", key="new_char_role", placeholder="例: ナレーター")
    if st.button("✨ 作成", type="primary", use_container_width=True):
        if not new_name.strip():
            st.error("表示名を入力してください")
        else:
            blank = make_empty_character(new_name.strip(), new_role.strip() or "ナレーター")
            saved = add_character(blank)
            st.session_state.selected_char_id = saved["id"]
            # Clear the input widgets via session_state
            for k in ("new_char_name", "new_char_role"):
                st.session_state.pop(k, None)
            st.rerun()

    st.divider()

    # ── Character list ─────────────────────────────────────────────────────────
    char_data = load_characters()
    chars     = char_data["characters"]
    default_id = char_data.get("default_character_id")

    st.subheader(f"キャラクター一覧  ({len(chars)})")
    if not chars:
        st.info("まだキャラクターがありません")
    else:
        for char in chars:
            is_def = char["id"] == default_id
            is_sel = char["id"] == st.session_state.selected_char_id
            label  = f"{'⭐ ' if is_def else ''}{char['basic']['display_name']}"
            role   = char["basic"].get("role", "")
            if role:
                label += f"  [{role}]"
            if st.button(
                label,
                key=f"sel_{char['id']}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state.selected_char_id = char["id"]
                st.rerun()

    st.divider()

    # ── Default character ──────────────────────────────────────────────────────
    st.subheader("⭐ デフォルトキャラクター")
    st.caption("一発生成で自動的に使用されます")

    if chars:
        id_options  = [None] + [c["id"] for c in chars]
        name_map    = {None: "（なし）"}
        name_map.update({c["id"]: c["basic"]["display_name"] for c in chars})
        def_idx = id_options.index(default_id) if default_id in id_options else 0
        new_default = st.selectbox(
            "デフォルト",
            id_options,
            format_func=lambda x: name_map.get(x, "不明"),
            index=def_idx,
            key="default_char_sel",
            label_visibility="collapsed",
        )
        if st.button("⭐ 設定を保存", use_container_width=True):
            set_default_character(new_default)
            st.success("デフォルトを更新しました")
            st.rerun()
    else:
        st.caption("キャラクターがありません")

    st.divider()
    st.caption(f"⚙️ `{_settings['ai']['model']}` | `{CHARACTERS_PATH.name}`")


# ── Re-load after possible sidebar mutations ───────────────────────────────────

char_data  = load_characters()
chars      = char_data["characters"]
default_id = char_data.get("default_character_id")


# ── Empty state ────────────────────────────────────────────────────────────────

if not chars:
    st.info(
        "まだキャラクターがありません。\n\n"
        "左のサイドバーの「新規作成」からキャラクターを追加してください。"
    )
    st.stop()


# ── List overview (no character selected) ─────────────────────────────────────

if not st.session_state.selected_char_id:
    st.info("👈 左のサイドバーからキャラクターを選択してください")
    st.subheader(f"キャラクター一覧 ({len(chars)} 件)")

    for char in chars:
        is_def = char["id"] == default_id
        badge  = "  ⭐ デフォルト" if is_def else ""
        with st.expander(
            f"{'★ ' if is_def else ''}**{char['basic']['display_name']}**"
            f"  [{char['basic'].get('role','')}]{badge}"
        ):
            c1, c2 = st.columns([1, 1])
            with c1:
                b = char["basic"]
                p = char["personality"]
                st.markdown(f"**年齢:** {b.get('age','-')}歳 | **性別:** {GENDER_LABELS.get(b.get('gender',''),'-')}")
                st.markdown(f"**性格:** {p.get('personality') or '-'}")
                st.markdown(f"**話し方:** {p.get('speaking_style') or '-'}")
                st.markdown(f"**一人称:** {p.get('first_person') or '-'}")
                if p.get("catch_phrase"):
                    st.markdown(f"**キャッチフレーズ:** {p['catch_phrase']}")
            with c2:
                img_base = char["prompt"].get("image_prompt_base", "")
                if img_base:
                    st.caption("画像プロンプトベース:")
                    st.code(img_base[:200], language=None)
                # Portrait thumbnail
                portrait = char["assets"].get("portrait")
                if portrait:
                    full = PROJECT_ROOT / portrait
                    if full.exists():
                        st.image(str(full), width=120)
            if st.button("✏️ 編集する", key=f"edit_{char['id']}", use_container_width=True):
                st.session_state.selected_char_id = char["id"]
                st.rerun()
    st.stop()


# ── Character editor ───────────────────────────────────────────────────────────

# Always reload fresh to pick up asset saves
char_data  = load_characters()
chars      = char_data["characters"]
default_id = char_data.get("default_character_id")
char       = next((c for c in chars if c["id"] == st.session_state.selected_char_id), None)

if not char:
    st.warning("キャラクターが見つかりません（削除された可能性があります）")
    st.session_state.selected_char_id = None
    st.rerun()

cid      = char["id"]
is_def   = cid == default_id

# Header
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.subheader(
        f"{'⭐ ' if is_def else ''}✏️ {char['basic']['display_name']}"
        f"  —  {char['basic'].get('role','')}"
    )
with hc2:
    if is_def:
        st.success("⭐ デフォルト")
    st.caption(f"ID: `{cid}`")
    st.caption(f"更新: {char.get('updated_at','')[:10]}")

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_basic, tab_app, tab_pers, tab_prompt, tab_assets = st.tabs([
    "📝 基本情報", "👤 外見", "🎭 性格", "🎨 プロンプト", "📁 アセット",
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — Basic
# ════════════════════════════════════════════════════════════════
with tab_basic:
    c1, c2 = st.columns(2)
    with c1:
        v_name = st.text_input(
            "表示名 *",
            value=char["basic"].get("display_name", ""),
            key=f"{cid}_name",
        )
        v_age = st.number_input(
            "年齢",
            value=int(char["basic"].get("age", 25)),
            min_value=0,
            max_value=150,
            step=1,
            key=f"{cid}_age",
        )
    with c2:
        _g    = char["basic"].get("gender", "female")
        _gidx = GENDER_OPTIONS.index(_g) if _g in GENDER_OPTIONS else 0
        v_gender = st.selectbox(
            "性別",
            GENDER_OPTIONS,
            index=_gidx,
            format_func=lambda x: GENDER_LABELS.get(x, x),
            key=f"{cid}_gender",
        )
        v_role = st.text_input(
            "役割",
            value=char["basic"].get("role", ""),
            key=f"{cid}_role",
            placeholder="例: ナレーター, 主人公, サブキャラ",
        )

# ════════════════════════════════════════════════════════════════
# TAB 2 — Appearance
# ════════════════════════════════════════════════════════════════
with tab_app:
    c1, c2 = st.columns(2)
    with c1:
        v_hairstyle  = st.text_input("髪型",       value=char["appearance"].get("hairstyle",""),   key=f"{cid}_hairstyle",   placeholder="例: ロング, ショート, ポニーテール")
        v_hair_color = st.text_input("髪色",       value=char["appearance"].get("hair_color",""),  key=f"{cid}_hair_color",  placeholder="例: 黒, 茶色, 金髪")
        v_eye_color  = st.text_input("瞳の色",     value=char["appearance"].get("eye_color",""),   key=f"{cid}_eye_color",   placeholder="例: 茶色, 青, 緑")
    with c2:
        v_clothing    = st.text_input("服装",       value=char["appearance"].get("clothing",""),    key=f"{cid}_clothing",    placeholder="例: スーツ, カジュアル, 制服")
        v_accessories = st.text_input("アクセサリー", value=char["appearance"].get("accessories",""), key=f"{cid}_accessories", placeholder="例: 眼鏡, イヤリング, 帽子")

    st.divider()
    st.caption("**外見プレビュー（画像プロンプト向け）**")
    _tmp_app = {
        "appearance": {
            "hairstyle":   st.session_state.get(f"{cid}_hairstyle",  char["appearance"].get("hairstyle","")),
            "hair_color":  st.session_state.get(f"{cid}_hair_color", char["appearance"].get("hair_color","")),
            "eye_color":   st.session_state.get(f"{cid}_eye_color",  char["appearance"].get("eye_color","")),
            "clothing":    st.session_state.get(f"{cid}_clothing",   char["appearance"].get("clothing","")),
            "accessories": st.session_state.get(f"{cid}_accessories",char["appearance"].get("accessories","")),
        },
        "prompt": char["prompt"],
    }
    st.code(preview_prompt(_tmp_app, "image") or "（未入力）", language=None)

# ════════════════════════════════════════════════════════════════
# TAB 3 — Personality
# ════════════════════════════════════════════════════════════════
with tab_pers:
    c1, c2 = st.columns(2)
    with c1:
        v_personality    = st.text_area(
            "性格",
            value=char["personality"].get("personality", ""),
            height=120,
            key=f"{cid}_personality",
            placeholder="例: 明るく知的、好奇心旺盛で親しみやすい",
        )
        v_speaking_style = st.text_input(
            "話し方",
            value=char["personality"].get("speaking_style", ""),
            key=f"{cid}_speaking_style",
            placeholder="例: 丁寧・解説調、フレンドリー、ですます調",
        )
    with c2:
        v_first_person = st.text_input(
            "一人称",
            value=char["personality"].get("first_person", "私"),
            key=f"{cid}_first_person",
            placeholder="私 / 僕 / 俺 / わたし など",
        )
        v_catch_phrase = st.text_input(
            "キャッチフレーズ",
            value=char["personality"].get("catch_phrase", ""),
            key=f"{cid}_catch_phrase",
            placeholder="例: では、一緒に学びましょう！",
        )

# ════════════════════════════════════════════════════════════════
# TAB 4 — Prompts
# ════════════════════════════════════════════════════════════════
with tab_prompt:
    v_image_prompt_base = st.text_area(
        "画像プロンプトベース",
        value=char["prompt"].get("image_prompt_base", ""),
        height=90,
        key=f"{cid}_img_base",
        help="各シーンの画像プロンプトに付加される固定テキスト（英語推奨）",
        placeholder="例: young Japanese woman, professional appearance, warm smile, studio lighting",
    )
    v_video_prompt_base = st.text_area(
        "動画プロンプトベース",
        value=char["prompt"].get("video_prompt_base", ""),
        height=90,
        key=f"{cid}_vid_base",
        help="各シーンの動画プロンプトに付加される固定テキスト（英語推奨）",
        placeholder="例: professional narrator, speaking to camera, natural hand gestures, bokeh background",
    )
    v_voice_description = st.text_area(
        "音声説明",
        value=char["prompt"].get("voice_description", ""),
        height=70,
        key=f"{cid}_voice_desc",
        help="音声合成ツールに渡す声のキャラクター説明",
        placeholder="例: 明るい女性の声、標準語、丁寧な話し方、落ち着いたテンポ",
    )

    st.divider()
    st.subheader("🔍 AIプロンプトプレビュー")
    st.caption("一発生成でこのキャラクターが選択されたときにAIに渡されるテキスト（保存後に更新）")
    st.code(character_to_prompt_snippet(char), language=None)

# ════════════════════════════════════════════════════════════════
# TAB 5 — Assets
# ════════════════════════════════════════════════════════════════
with tab_assets:
    assets    = char.get("assets", {"portrait": None, "expressions": [], "voice_sample": None})
    assets_dir = PROJECT_ROOT / "assets" / "characters" / cid

    # ── Portrait ──────────────────────────────────────────────
    st.subheader("🖼️ ポートレート")
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        portrait_rel = assets.get("portrait")
        if portrait_rel:
            p_full = PROJECT_ROOT / portrait_rel
            if p_full.exists():
                st.image(str(p_full), width=180)
            else:
                st.warning("画像が見つかりません")
        else:
            st.caption("未設定")
    with pc2:
        up_portrait = st.file_uploader(
            "ポートレートをアップロード",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"up_portrait_{cid}",
        )
        if up_portrait:
            assets_dir.mkdir(parents=True, exist_ok=True)
            dest = assets_dir / f"portrait{Path(up_portrait.name).suffix}"
            dest.write_bytes(up_portrait.getvalue())
            rel = str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/")
            edit_character(cid, {"assets": {"portrait": rel}})
            st.success("ポートレートを保存しました ✅")
            st.rerun()
        if portrait_rel:
            if st.button("🗑️ ポートレートを削除", key=f"del_portrait_{cid}"):
                edit_character(cid, {"assets": {"portrait": None}})
                st.rerun()

    st.divider()

    # ── Expression images ──────────────────────────────────────
    st.subheader("😊 表情画像")
    expressions = assets.get("expressions") or []

    if expressions:
        ncols = min(len(expressions), 5)
        exp_cols = st.columns(ncols)
        for i, (col, ep) in enumerate(zip(exp_cols, expressions)):
            ep_full = PROJECT_ROOT / ep
            if ep_full.exists():
                col.image(str(ep_full), width=110, caption=Path(ep).stem)
            else:
                col.warning("不明")
            if col.button("🗑️", key=f"del_expr_{cid}_{i}"):
                new_list = [e for j, e in enumerate(expressions) if j != i]
                edit_character(cid, {"assets": {"expressions": new_list}})
                st.rerun()
    else:
        st.caption("表情画像がありません")

    up_exprs = st.file_uploader(
        "表情画像を追加（複数可）",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key=f"up_exprs_{cid}",
    )
    if up_exprs:
        assets_dir.mkdir(parents=True, exist_ok=True)
        new_paths = list(expressions)
        for f in up_exprs:
            dest = assets_dir / f"expr_{len(new_paths):02d}_{f.name}"
            dest.write_bytes(f.getvalue())
            rel = str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if rel not in new_paths:
                new_paths.append(rel)
        edit_character(cid, {"assets": {"expressions": new_paths}})
        st.success(f"{len(up_exprs)} 件の表情画像を保存しました ✅")
        st.rerun()

    st.divider()

    # ── Voice sample ───────────────────────────────────────────
    st.subheader("🎙️ 音声サンプル")
    voice_rel = assets.get("voice_sample")
    if voice_rel:
        v_full = PROJECT_ROOT / voice_rel
        if v_full.exists():
            st.audio(v_full.read_bytes())
            st.caption(Path(voice_rel).name)
        else:
            st.warning("音声ファイルが見つかりません")
        if st.button("🗑️ 音声サンプルを削除", key=f"del_voice_{cid}"):
            edit_character(cid, {"assets": {"voice_sample": None}})
            st.rerun()
    else:
        st.caption("音声サンプルがありません")

    up_voice = st.file_uploader(
        "音声サンプルをアップロード",
        type=["mp3", "wav", "m4a", "ogg", "flac"],
        key=f"up_voice_{cid}",
    )
    if up_voice:
        assets_dir.mkdir(parents=True, exist_ok=True)
        dest = assets_dir / f"voice_sample{Path(up_voice.name).suffix}"
        dest.write_bytes(up_voice.getvalue())
        rel = str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/")
        edit_character(cid, {"assets": {"voice_sample": rel}})
        st.success("音声サンプルを保存しました ✅")
        st.rerun()

# ── Action buttons ─────────────────────────────────────────────────────────────

st.divider()
btn_save, btn_dup, btn_gap = st.columns([3, 1, 2])

if btn_save.button("💾 変更を保存", type="primary", use_container_width=True):
    updates = {
        "basic": {
            "display_name": v_name,
            "age":          int(v_age),
            "gender":       v_gender,
            "role":         v_role,
        },
        "appearance": {
            "hairstyle":   v_hairstyle,
            "hair_color":  v_hair_color,
            "eye_color":   v_eye_color,
            "clothing":    v_clothing,
            "accessories": v_accessories,
        },
        "personality": {
            "personality":    v_personality,
            "speaking_style": v_speaking_style,
            "first_person":   v_first_person,
            "catch_phrase":   v_catch_phrase,
        },
        "prompt": {
            "image_prompt_base": v_image_prompt_base,
            "video_prompt_base": v_video_prompt_base,
            "voice_description": v_voice_description,
        },
    }
    edit_character(cid, updates)
    st.success("保存しました ✅")
    st.rerun()

if btn_dup.button("📋 複製", use_container_width=True):
    new_char = duplicate_character(cid)
    if new_char:
        st.session_state.selected_char_id = new_char["id"]
        st.success(f"複製しました: {new_char['basic']['display_name']}")
        st.rerun()

with st.expander("⚠️ 危険な操作"):
    confirm_del = st.checkbox(
        f"**{char['basic']['display_name']}** を削除することを確認",
        key=f"confirm_del_{cid}",
    )
    if st.button(
        "🗑️ 削除する",
        disabled=not confirm_del,
        key=f"del_btn_{cid}",
        use_container_width=True,
    ):
        delete_character(cid)
        st.session_state.selected_char_id = None
        st.success("削除しました")
        st.rerun()
