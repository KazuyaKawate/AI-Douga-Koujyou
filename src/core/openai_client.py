from openai import OpenAI
from src.utils.config import OPENAI_API_KEY


def generate_script(topic: str, duration: str, style: str, target: str, additional: str = "") -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""あなたはプロの動画ライターです。以下の条件で動画台本を作成してください。

テーマ: {topic}
動画の長さ: {duration}
スタイル: {style}
ターゲット視聴者: {target}
{f"追加指示: {additional}" if additional else ""}

以下の構成で台本を作成してください：
【冒頭（フック）】視聴者を引きつける導入
【本編】各セクションのナレーション
【まとめ・CTA】行動を促す締め

ナレーターが読み上げる形式で、自然な日本語で記述してください。"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000,
    )

    return response.choices[0].message.content
