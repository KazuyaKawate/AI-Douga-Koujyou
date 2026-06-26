"""Manual image provider — copy-ready instructions for manual image generation."""

NAME            = "Manual"
IS_MANUAL       = True
SUPPORTED_TOOLS = ["Nano Banana", "Midjourney", "DALL-E 3", "Adobe Firefly", "Runway Image"]


def is_available() -> bool:
    return True


def get_instructions(image_prompt: str, negative_prompt: str = "") -> str:
    lines = [
        f"対応ツール: {', '.join(SUPPORTED_TOOLS)}",
        "",
        "1. 以下のプロンプトをコピーして画像生成ツールに貼り付けてください",
        "",
        "【プロンプト】",
        image_prompt,
    ]
    if negative_prompt:
        lines += ["", "【ネガティブプロンプト】", negative_prompt]
    lines += [
        "",
        "2. 生成した画像を assets/images/ に保存してください",
        "   例: EP01_scene_01.png, EP01_scene_02.png",
    ]
    return "\n".join(lines)


def run(image_prompt: str, **kwargs) -> dict:
    return {
        "status":       "manual",
        "instructions": get_instructions(image_prompt, kwargs.get("negative_prompt", "")),
        "provider":     NAME,
    }
