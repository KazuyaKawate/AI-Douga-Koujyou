"""Manual audio provider — copy-ready instructions for voice, BGM, and SE production."""

NAME        = "Manual"
IS_MANUAL   = True
VOICE_TOOLS = ["Nano Banana", "ElevenLabs", "VOICEVOX", "Coeiroink", "AIVIS Speech"]
BGM_TOOLS   = ["Suno AI", "Udio", "Mubert", "royalty-free music library"]
SE_TOOLS    = ["Freesound.org", "ZapSplat", "Pixabay Sound Effects"]


def is_available() -> bool:
    return True


def get_voice_instructions(voice_script: str, voice_description: str = "") -> str:
    lines = [
        f"対応ツール: {', '.join(VOICE_TOOLS)}",
        "",
    ]
    if voice_description:
        lines += ["【音声設定】", voice_description, ""]
    lines += [
        "【音声台本】",
        voice_script,
        "",
        "1. 上記の台本をTTSツールに入力して音声を生成してください",
        "2. 生成した音声ファイルを voices/ に保存してください",
        "   例: EP01_narration.mp3",
    ]
    return "\n".join(lines)


def get_bgm_instructions(mood: str = "", duration_seconds: int = 0) -> str:
    lines = [f"対応ツール: {', '.join(BGM_TOOLS)}", ""]
    if mood:
        lines += [f"推奨ムード: {mood}", ""]
    if duration_seconds:
        lines += [f"必要な長さ: {duration_seconds}秒以上", ""]
    lines += [
        "1. ムードに合ったBGMを選択・生成してください",
        "2. BGMファイルを voices/ に保存してください",
        "   例: EP01_bgm.mp3",
    ]
    return "\n".join(lines)


def get_se_instructions() -> str:
    return (
        f"対応ツール: {', '.join(SE_TOOLS)}\n\n"
        "1. 必要な効果音を取得してください\n"
        "2. SEファイルを voices/ に保存してください\n"
        "   例: EP01_se_intro.wav"
    )


def run(voice_script: str, **kwargs) -> dict:
    return {
        "status":       "manual",
        "instructions": get_voice_instructions(voice_script, kwargs.get("voice_description", "")),
        "provider":     NAME,
    }
