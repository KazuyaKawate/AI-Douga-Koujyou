"""Project health check script for AI動画工場."""
import io
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent

REQUIRED_FOLDERS = [
    "assets",
    "assets/images",
    "assets/videos",
    "assets/voices",
    "config",
    "pages",
    "project",
    "src",
    "src/core",
    "src/utils",
    "src/pipeline",
    "src/providers",
    "src/director",
]

REQUIRED_FILES = [
    "app.py",
    "requirements.txt",
    # Pages
    "pages/6_Produce.py",
    "pages/8_Dashboard.py",
    "pages/9_Settings.py",
    "pages/10_Characters.py",
    "pages/11_Backgrounds.py",
    "pages/12_Prompt_Builder.py",
    "pages/13_Production.py",
    "pages/14_Director.py",
    # Core
    "src/core/ai_pipeline.py",
    "src/core/episode_manager.py",
    # Utils
    "src/utils/config.py",
    "src/utils/settings_manager.py",
    "src/utils/character_manager.py",
    "src/utils/background_manager.py",
    "src/utils/prompt_builder.py",
    # Pipeline
    "src/pipeline/__init__.py",
    "src/pipeline/script_pipeline.py",
    "src/pipeline/image_pipeline.py",
    "src/pipeline/video_pipeline.py",
    "src/pipeline/audio_pipeline.py",
    "src/pipeline/export_pipeline.py",
    # Providers
    "src/providers/__init__.py",
    "src/providers/openai_provider.py",
    "src/providers/image_provider_manual.py",
    "src/providers/video_provider_manual.py",
    "src/providers/audio_provider_manual.py",
    # Director
    "src/director/__init__.py",
    "src/director/director_schema.py",
    "src/director/director_planner.py",
]

OPTIONAL_FILES = [
    ".env",
    "config/settings.json",
    "config/characters.json",
    "config/backgrounds.json",
    "config/prompt_templates.json",
]


def check() -> bool:
    ok = True
    width = 60

    print("=" * width)
    print("  AI動画工場 — Project Health Check")
    print("=" * width)
    print(f"  Root: {ROOT}\n")

    # Folders
    print("[ フォルダ ]")
    for rel in REQUIRED_FOLDERS:
        p = ROOT / rel
        status = "OK  " if p.is_dir() else "MISS"
        if not p.is_dir():
            ok = False
        print(f"  [{status}] {rel}")

    print()

    # Required files
    print("[ 必須ファイル ]")
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if p.exists():
            kb = p.stat().st_size / 1024
            print(f"  [OK  ] {rel}  ({kb:.1f} KB)")
        else:
            print(f"  [MISS] {rel}")
            ok = False

    print()

    # Optional
    print("[ オプション ]")
    for rel in OPTIONAL_FILES:
        p = ROOT / rel
        if p.exists():
            print(f"  [OK  ] {rel}")
        else:
            print(f"  [----] {rel}  (未作成)")

    print()

    # Config JSON check
    print("[ 設定ファイル ]")
    import json
    for cfg_name, key in [
        ("config/settings.json",         None),
        ("config/characters.json",        "characters"),
        ("config/backgrounds.json",       "backgrounds"),
        ("config/prompt_templates.json",  "templates"),
    ]:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key:
                    count = len(data.get(key, []))
                    print(f"  [OK  ] {cfg_name}  ({count} {key})")
                else:
                    print(f"  [OK  ] {cfg_name}")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")

    print()

    # Episode count
    print("[ エピソード ]")
    project_dir = ROOT / "project"
    if project_dir.exists():
        eps = [d for d in project_dir.iterdir() if d.is_dir() and (d / "episode.json").exists()]
        with_director = [e for e in eps if (e / "director_plan.json").exists()]
        with_export   = [e for e in eps if (e / "export" / "production_report.json").exists()]
        print(f"  エピソード総数: {len(eps)}")
        print(f"  演出計画あり:   {len(with_director)}")
        print(f"  書き出し済み:   {len(with_export)}")
    else:
        print("  project/ フォルダが存在しません")

    print()
    print("=" * width)
    if ok:
        print("  STATUS: OK — すべての必須ファイルが揃っています ✅")
    else:
        print("  STATUS: NG — 不足ファイルがあります ❌")
    print("=" * width)

    return ok


if __name__ == "__main__":
    success = check()
    sys.exit(0 if success else 1)
