import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.core import episode_manager as em

st.set_page_config(page_title="素材ライブラリ", page_icon="📚", layout="wide")
st.title("📚 素材ライブラリ")
st.caption("制作素材を一元管理し、エピソードへのアサインと素材メモを保存 | v2.2")

# ── Constants ─────────────────────────────────────────────────────────────────

ASSETS_ROOT = PROJECT_ROOT / "assets"
NOTES_PATH = PROJECT_ROOT / "config" / "assets_notes.json"

CATEGORIES = [
    ("キャラクター素材", "characters", "🎭"),
    ("背景素材",         "backgrounds", "🌄"),
    ("生成画像",         "images",      "🖼️"),
    ("動画素材",         "videos",      "🎬"),
    ("音声素材",         "voices",      "🎙️"),
    ("BGM",              "BGM",         "🎵"),
    ("SE",               "SE",          "🔊"),
]

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".webm"}
TEXT_EXT  = {".txt", ".srt", ".json", ".md", ".csv"}

PREVIEW_LIMIT = 20 * 1024 * 1024  # skip preview for files > 20 MB
TEXT_PREVIEW_CHARS = 600


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rel(f: Path) -> str:
    return str(f.relative_to(PROJECT_ROOT)).replace("\\", "/")

def _safe(rel: str) -> str:
    # Create a widget-key-safe string from a relative path
    return rel.replace("/", "__").replace(".", "_").replace(" ", "_")

def _note_key(rel: str) -> str:
    return f"astnote__{_safe(rel)}"

def _sel_key(rel: str) -> str:
    return f"astsel__{_safe(rel)}"


def load_notes() -> dict:
    if NOTES_PATH.exists():
        try:
            return json.loads(NOTES_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_all_notes() -> int:
    notes: dict[str, str] = {}
    for _, folder_name, _ in CATEGORIES:
        folder = ASSETS_ROOT / folder_name
        if not folder.exists():
            continue
        for f in folder.iterdir():
            if f.is_file():
                rel = _rel(f)
                val = st.session_state.get(_note_key(rel), "").strip()
                if val:
                    notes[rel] = val
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTES_PATH.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(notes)


def get_selected_assets() -> list[dict]:
    selected = []
    for _, folder_name, _ in CATEGORIES:
        folder = ASSETS_ROOT / folder_name
        if not folder.exists():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file():
                rel = _rel(f)
                if st.session_state.get(_sel_key(rel), False):
                    selected.append({
                        "path": rel,
                        "filename": f.name,
                        "type": folder_name,
                        "note": st.session_state.get(_note_key(rel), "").strip(),
                    })
    return selected


def fmt_size(n_bytes: int) -> str:
    if n_bytes < 1024:
        return f"{n_bytes} B"
    if n_bytes < 1024 ** 2:
        return f"{n_bytes / 1024:.1f} KB"
    return f"{n_bytes / 1024 ** 2:.2f} MB"


# ── Bootstrap: create folders, load notes ─────────────────────────────────────

for _, folder_name, _ in CATEGORIES:
    (ASSETS_ROOT / folder_name).mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "config").mkdir(parents=True, exist_ok=True)

# Preload saved notes into session_state (once per session)
if "ast_notes_loaded" not in st.session_state:
    for rel_path, note_text in load_notes().items():
        key = _note_key(rel_path)
        if key not in st.session_state:
            st.session_state[key] = note_text
    st.session_state["ast_notes_loaded"] = True


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader("操作")

    if st.button("💾 メモを全て保存", type="primary", use_container_width=True):
        n = save_all_notes()
        st.success(f"{n} 件のメモを保存しました")

    st.divider()
    st.subheader("📋 素材リストをエクスポート")
    st.caption("チェックした素材をエピソードのマニフェストに書き出します")

    ep_ids = em.get_episode_list()
    if ep_ids:
        target_ep = st.selectbox("エピソードID", ep_ids, key="manifest_ep_id")
        if st.button("📋 asset_manifest.json を出力", use_container_width=True):
            selected = get_selected_assets()
            if not selected:
                st.warning("素材を1件以上チェックしてください")
            else:
                manifest = {
                    "episode_id": target_ep,
                    "created_at": datetime.now().isoformat(),
                    "asset_count": len(selected),
                    "assets": selected,
                }
                out = PROJECT_ROOT / "project" / target_ep / "asset_manifest.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                st.success(
                    f"{len(selected)} 件を出力\n"
                    f"`project/{target_ep}/asset_manifest.json`"
                )
    else:
        st.caption(
            "エピソードがまだありません。\n"
            "⚡ 一発生成 でエピソードを作成してください。"
        )

    st.divider()
    _s = load_settings()
    st.caption(
        f"⚙️ 画像: `{_s['generation']['image_provider']}`"
        f" | 動画: `{_s['generation']['video_provider']}`"
        f" | 音声: `{_s['generation']['voice_provider']}`"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

# File totals
total_files = sum(
    sum(1 for f in (ASSETS_ROOT / fn).iterdir() if f.is_file())
    for _, fn, _ in CATEGORIES
    if (ASSETS_ROOT / fn).exists()
)
st.caption(f"合計 {total_files} ファイル | フォルダ: `{ASSETS_ROOT}`")

if total_files == 0:
    st.info(
        "素材フォルダにファイルがありません。\n\n"
        "生成した画像・動画・音声ファイルを以下のフォルダに追加してください:\n\n"
        + "  ".join(f"`assets/{fn}/`" for _, fn, _ in CATEGORIES)
    )

# ── Asset sections ─────────────────────────────────────────────────────────────

for cat_label, folder_name, icon in CATEGORIES:
    folder = ASSETS_ROOT / folder_name
    files = (
        sorted(
            (f for f in folder.iterdir() if f.is_file()),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if folder.exists()
        else []
    )

    with st.expander(
        f"{icon} {cat_label} — {len(files)} ファイル",
        expanded=(len(files) > 0),
    ):
        if not files:
            st.caption(
                f"空のフォルダ: `assets/{folder_name}/`\n"
                f"このフォルダに素材ファイルを追加してください。"
            )
            continue

        for f in files:
            rel   = _rel(f)
            stat  = f.stat()
            ext   = f.suffix.lower()
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

            c_info, c_preview, c_note = st.columns([2, 3, 3])

            # ── Info + selection checkbox ──
            with c_info:
                st.checkbox(
                    f.name,
                    key=_sel_key(rel),
                    help=f"マニフェストに追加: {rel}",
                )
                st.caption(f"{fmt_size(stat.st_size)} | {mtime}")
                st.caption(f"`{rel}`")

            # ── Preview ──
            with c_preview:
                oversized = stat.st_size > PREVIEW_LIMIT
                if oversized:
                    st.caption(f"ファイルサイズが大きいためプレビュー省略 ({fmt_size(stat.st_size)})")
                elif ext in IMAGE_EXT:
                    try:
                        st.image(str(f), use_container_width=True)
                    except Exception as e:
                        st.caption(f"画像読み込みエラー: {e}")
                elif ext in AUDIO_EXT:
                    try:
                        st.audio(f.read_bytes())
                    except Exception as e:
                        st.caption(f"音声読み込みエラー: {e}")
                elif ext in VIDEO_EXT:
                    try:
                        st.video(f.read_bytes())
                    except Exception as e:
                        st.caption(f"動画読み込みエラー: {e}")
                elif ext in TEXT_EXT:
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                        snippet = text[:TEXT_PREVIEW_CHARS]
                        if len(text) > TEXT_PREVIEW_CHARS:
                            snippet += "\n..."
                        st.code(snippet, language=None)
                    except Exception as e:
                        st.caption(f"テキスト読み込みエラー: {e}")
                else:
                    st.caption("プレビュー非対応")

            # ── Notes ──
            with c_note:
                st.text_area(
                    "素材メモ",
                    height=110,
                    key=_note_key(rel),
                    label_visibility="collapsed",
                    placeholder=f"{f.name} のメモ（用途・出典・注意点など）",
                )

            st.divider()
