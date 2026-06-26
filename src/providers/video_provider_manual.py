"""Manual video provider — copy-ready instructions for manual video generation."""

NAME            = "Manual"
IS_MANUAL       = True
SUPPORTED_TOOLS = ["Runway Gen-3 Alpha", "Pika Labs", "Stable Video Diffusion", "Kling AI"]


def is_available() -> bool:
    return True


def get_instructions(video_prompt: str, duration_seconds: int = 5) -> str:
    lines = [
        f"対応ツール: {', '.join(SUPPORTED_TOOLS)}",
        "",
        f"目標クリップ長: {duration_seconds}秒",
        "",
        "1. 以下のプロンプトをコピーして動画生成ツールに貼り付けてください",
        "",
        "【プロンプト】",
        video_prompt,
        "",
        "2. 生成した動画クリップを videos/ に保存してください",
        "   例: EP01_scene_01.mp4, EP01_scene_02.mp4",
    ]
    return "\n".join(lines)


def run(video_prompt: str, **kwargs) -> dict:
    return {
        "status":       "manual",
        "instructions": get_instructions(video_prompt, kwargs.get("duration_seconds", 5)),
        "provider":     NAME,
    }
