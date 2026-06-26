import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import OPENAI_API_KEY, PROJECT_ROOT

st.set_page_config(page_title="台本生成", page_icon="📝", layout="wide")
st.title("📝 台本生成")
st.caption("OpenAI GPT でテーマから台本・ナレーション原稿を自動生成します")

if not OPENAI_API_KEY:
    st.warning("⚠️ OpenAI API キーが未設定です。プロジェクトルートに `.env` ファイルを作成し `OPENAI_API_KEY` を設定してください。")

with st.form("script_form"):
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("テーマ・タイトル *", placeholder="例: Pythonプログラミング入門")
        target = st.text_input("ターゲット視聴者", placeholder="例: プログラミング初心者")
    with col2:
        duration = st.selectbox("動画の長さ", ["1分", "3分", "5分", "10分"])
        style = st.selectbox("スタイル", ["解説・教育", "エンタメ", "ニュース", "ドキュメンタリー", "Vlog"])
    additional = st.text_area("追加指示（任意）", placeholder="例: 専門用語を使わず、初心者でも分かりやすく")
    submitted = st.form_submit_button("台本を生成する 🚀", type="primary")

if submitted:
    if not topic:
        st.error("テーマを入力してください")
    elif not OPENAI_API_KEY:
        st.error("OpenAI API キーを設定してください")
    else:
        from src.core.openai_client import generate_script

        with st.spinner("台本を生成中..."):
            try:
                script = generate_script(topic, duration, style, target, additional)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                script = None

        if script:
            st.success("台本の生成が完了しました！")
            st.text_area("生成された台本", value=script, height=450)

            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{topic[:20].replace(' ', '_')}.txt"
            save_path = PROJECT_ROOT / "scripts" / filename

            col1, col2 = st.columns(2)
            if col1.button("💾 scripts/ に保存", use_container_width=True):
                save_path.write_text(script, encoding="utf-8")
                st.success(f"保存しました: `scripts/{filename}`")
            col2.download_button(
                "⬇️ ダウンロード",
                data=script,
                file_name=filename,
                mime="text/plain",
                use_container_width=True,
            )

st.divider()
st.subheader("保存済み台本")
scripts_dir = PROJECT_ROOT / "scripts"
scripts = list(scripts_dir.glob("*.txt")) if scripts_dir.exists() else []
if scripts:
    selected = st.selectbox("ファイルを選択", [f.name for f in sorted(scripts, key=lambda x: x.stat().st_mtime, reverse=True)])
    if selected:
        content = (scripts_dir / selected).read_text(encoding="utf-8")
        st.text_area("内容", value=content, height=300)
else:
    st.info("scripts/ に台本ファイルがありません")
