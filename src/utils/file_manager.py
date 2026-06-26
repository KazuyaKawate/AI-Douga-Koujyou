from pathlib import Path
from datetime import datetime


def count_files(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.iterdir() if f.is_file())


def list_files(folder: Path, extensions: list[str] | None = None) -> list[Path]:
    if not folder.exists():
        return []
    files = [f for f in folder.rglob("*") if f.is_file()]
    if extensions:
        files = [f for f in files if f.suffix.lower() in extensions]
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)


def file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "ファイル名": path.name,
        "サイズ": f"{stat.st_size / 1024:.1f} KB",
        "更新日時": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
    }
