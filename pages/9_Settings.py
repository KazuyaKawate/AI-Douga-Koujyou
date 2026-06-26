import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.settings_manager import CONFIG_PATH, DEFAULTS, load_settings, save_settings, _copy

st.set_page_config(page_title="スタジオ設定", page_icon="⚙️", layout="wide")
st.title("⚙️ スタジオ設定")
st.caption("プロジェクト・AI・生成プロバイダーの設定を管理 | v2.6")

# ── Constants ──────────────────────────────────────────────────────────────────

EPISODE_LENGTHS  = ["1分", "2分", "3分", "5分", "10分"]
ASPECT_RATIOS    = ["16:9", "9:16", "1:1", "4:3"]
FPS_OPTIONS      = [24, 25, 30, 60]
RESOLUTIONS      = ["1920x1080", "1280x720", "3840x2160", "1080x1920", "1080x1080", "720x1280"]
MODELS           = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
PROVIDERS        = ["Manual", "Nano Banana", "Runway"]
PROVIDER_LABELS  = {
    "Manual":      "Manual（手動）",
    "Nano Banana": "Nano Banana（将来実装予定）",
    "Runway":      "Runway（将来実装予定）",
}

EXPORT_SPECS = {
    "youtube_shorts": ("YouTube Shorts",   "9:16 | 1080×1920 | 最大60秒"),
    "tiktok":         ("TikTok",           "9:16 | 1080×1920 | 最大180秒"),
    "instagram_reels":("Instagram Reels",  "9:16 | 1080×1920 | 最大90秒"),
}


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader("設定ファイル")
    st.code(str(CONFIG_PATH), language=None)
    if CONFIG_PATH.exists():
        st.success("設定ファイルが存在します")
    else:
        st.warning("未保存（デフォルト値を使用中）")
    st.divider()
    st.caption("設定は保存後、次回の各ページ読み込み時に反映されます。")


# ── Load current settings ──────────────────────────────────────────────────────

cfg = load_settings()
p   = cfg["project"]
ai  = cfg["ai"]
gen = cfg["generation"]
exp = cfg["export"]


# ── Helper: safe index lookup ──────────────────────────────────────────────────

def _idx(options: list, value, default: int = 0) -> int:
    try:
        return options.index(value)
    except ValueError:
        return default


# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_proj, tab_ai, tab_gen, tab_exp = st.tabs([
    "📁 プロジェクト",
    "🤖 AI",
    "🎨 生成プロバイダー",
    "📤 エクスポート",
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — プロジェクト
# ════════════════════════════════════════════════════════════════
with tab_proj:
    st.subheader("📁 プロジェクト設定")

    c1, c2 = st.columns(2)

    with c1:
        v_output_folder = st.text_input(
            "デフォルト出力フォルダ",
            value=p["default_output_folder"],
            help="最終動画の出力先フォルダ名（PROJECT_ROOT 直下）",
        )
        v_ep_length = st.selectbox(
            "デフォルトエピソード長",
            EPISODE_LENGTHS,
            index=_idx(EPISODE_LENGTHS, p["default_episode_length"], 2),
            help="一発生成・台本生成での初期値",
        )
        v_scene_count = st.slider(
            "デフォルトシーン数",
            min_value=2,
            max_value=8,
            value=int(p["default_scene_count"]),
            help="一発生成でのシーン数初期値",
        )

    with c2:
        v_aspect_ratio = st.selectbox(
            "動画アスペクト比",
            ASPECT_RATIOS,
            index=_idx(ASPECT_RATIOS, p["video_aspect_ratio"]),
            help="画像・動画プロンプトのデフォルト比率",
        )
        v_fps = st.selectbox(
            "FPS",
            FPS_OPTIONS,
            index=_idx(FPS_OPTIONS, int(p["fps"]), 2),
            help="動画組立時のデフォルトフレームレート",
        )
        v_resolution = st.selectbox(
            "解像度",
            RESOLUTIONS,
            index=_idx(RESOLUTIONS, p["resolution"]),
            help="動画の出力解像度",
        )

    st.caption(
        f"現在: `{v_aspect_ratio}` | `{v_resolution}` | `{v_fps}fps`"
        f" | デフォルト尺 `{v_ep_length}` | シーン数 `{v_scene_count}`"
    )

# ════════════════════════════════════════════════════════════════
# TAB 2 — AI
# ════════════════════════════════════════════════════════════════
with tab_ai:
    st.subheader("🤖 AI設定")

    c1, c2 = st.columns(2)

    with c1:
        v_model = st.selectbox(
            "AIモデル",
            MODELS,
            index=_idx(MODELS, ai["model"]),
            help="OpenAI モデルを選択（gpt-4o-mini が最もコスト効率が高い）",
        )
        v_dev_mode = st.checkbox(
            "開発モード",
            value=bool(ai["dev_mode"]),
            help="有効にすると外部生成API（画像/動画/音声）を呼ばない旨の警告を表示します",
        )
        v_cost_saving = st.checkbox(
            "コスト節約モード",
            value=bool(ai["cost_saving"]),
            help="プロンプトを短くして OpenAI トークン消費を削減します（2〜3シーン推奨）",
        )

    with c2:
        v_temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.5,
            value=float(ai["temperature"]),
            step=0.05,
            help="0に近いほど決定論的、高いほど多様な出力になります",
        )
        v_max_tokens = st.slider(
            "Max Tokens",
            min_value=500,
            max_value=8000,
            value=int(ai["max_tokens"]),
            step=500,
            help="コスト節約モード時は自動的に 1500 に制限されます",
        )

    st.info(
        f"現在のモデル: **{v_model}**  \n"
        f"Temperature: `{v_temperature}`  |  Max Tokens: `{v_max_tokens}`  \n"
        f"{'🔧 開発モード有効' if v_dev_mode else '🚀 本番モード'}  |  "
        f"{'💰 節約モード有効' if v_cost_saving else '⚡ 標準モード'}"
    )

# ════════════════════════════════════════════════════════════════
# TAB 3 — 生成プロバイダー
# ════════════════════════════════════════════════════════════════
with tab_gen:
    st.subheader("🎨 生成プロバイダー")
    st.caption("各素材の生成ツールを選択します。Manual 以外は将来の統合予定です。")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**🖼️ 画像プロバイダー**")
        v_image_provider = st.selectbox(
            "画像",
            PROVIDERS,
            index=_idx(PROVIDERS, gen["image_provider"]),
            format_func=lambda x: PROVIDER_LABELS.get(x, x),
            label_visibility="collapsed",
        )
        if v_image_provider != "Manual":
            st.warning("このプロバイダーは将来実装予定です。現在は Manual（手動）として動作します。", icon="⚠️")
        else:
            st.success("Midjourney / Nano Banana 等を手動で使用", icon="✅")

    with c2:
        st.markdown("**🎬 動画プロバイダー**")
        v_video_provider = st.selectbox(
            "動画",
            PROVIDERS,
            index=_idx(PROVIDERS, gen["video_provider"]),
            format_func=lambda x: PROVIDER_LABELS.get(x, x),
            label_visibility="collapsed",
        )
        if v_video_provider != "Manual":
            st.warning("このプロバイダーは将来実装予定です。現在は Manual（手動）として動作します。", icon="⚠️")
        else:
            st.success("Runway Gen-3 等を手動で使用", icon="✅")

    with c3:
        st.markdown("**🎙️ 音声プロバイダー**")
        v_voice_provider = st.selectbox(
            "音声",
            PROVIDERS,
            index=_idx(PROVIDERS, gen["voice_provider"]),
            format_func=lambda x: PROVIDER_LABELS.get(x, x),
            label_visibility="collapsed",
        )
        if v_voice_provider != "Manual":
            st.warning("このプロバイダーは将来実装予定です。現在は Manual（手動）として動作します。", icon="⚠️")
        else:
            st.success("Nano Banana / VOICEVOX 等を手動で使用", icon="✅")

# ════════════════════════════════════════════════════════════════
# TAB 4 — エクスポート
# ════════════════════════════════════════════════════════════════
with tab_exp:
    st.subheader("📤 エクスポートプリセット")
    st.caption("有効にしたプラットフォーム向けのフォーマット設定で書き出します（将来実装予定）。")

    v_yt_shorts = v_tiktok = v_ig_reels = False

    for key, (label, spec) in EXPORT_SPECS.items():
        col_chk, col_spec = st.columns([1, 3])
        with col_chk:
            val = col_chk.checkbox(label, value=bool(exp.get(key, False)), key=f"exp_{key}")
            if key == "youtube_shorts":
                v_yt_shorts = val
            elif key == "tiktok":
                v_tiktok = val
            elif key == "instagram_reels":
                v_ig_reels = val
        with col_spec:
            st.caption(spec)

    active = [label for key, (label, _) in EXPORT_SPECS.items() if exp.get(key, False)]
    if active:
        st.info(f"有効なプリセット: {', '.join(active)}")
    else:
        st.caption("現在有効なエクスポートプリセットはありません")


# ── Save / Reset ───────────────────────────────────────────────────────────────

st.divider()
col_save, col_reset = st.columns([3, 1])

with col_save:
    if st.button("💾 設定を保存", type="primary", use_container_width=True):
        new_cfg = {
            "project": {
                "default_output_folder": v_output_folder,
                "default_episode_length": v_ep_length,
                "default_scene_count": v_scene_count,
                "video_aspect_ratio": v_aspect_ratio,
                "fps": v_fps,
                "resolution": v_resolution,
            },
            "ai": {
                "model": v_model,
                "dev_mode": v_dev_mode,
                "cost_saving": v_cost_saving,
                "temperature": v_temperature,
                "max_tokens": v_max_tokens,
            },
            "generation": {
                "image_provider": v_image_provider,
                "video_provider": v_video_provider,
                "voice_provider": v_voice_provider,
            },
            "export": {
                "youtube_shorts": v_yt_shorts,
                "tiktok": v_tiktok,
                "instagram_reels": v_ig_reels,
            },
        }
        save_settings(new_cfg)
        st.success(f"設定を保存しました ✅  `{CONFIG_PATH}`")
        st.rerun()

with col_reset:
    confirm_reset = st.checkbox("リセットを確認", key="confirm_reset")
    if st.button("↩️ デフォルトに戻す", disabled=not confirm_reset, use_container_width=True):
        save_settings(_copy(DEFAULTS))
        st.success("デフォルト設定に戻しました")
        st.rerun()


# ── JSON preview ───────────────────────────────────────────────────────────────

with st.expander("📄 現在の設定 (JSON)"):
    st.json(load_settings())
