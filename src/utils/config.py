import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OFFICIAL_WORKSPACE = PROJECT_ROOT
DOTENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=DOTENV_PATH, override=False)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

FOLDERS = {
    "台本": "scripts",
    "画像": "images",
    "動画": "videos",
    "音声": "voices",
    "字幕": "subtitles",
    "完成動画": "output",
    "一時ファイル": "temp",
    "エピソード": "project",
}

