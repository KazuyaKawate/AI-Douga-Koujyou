"""Playwright と Chromium のインストール。
初回のみ実行してください: python scripts/install_playwright.py
"""
import subprocess
import sys


def run(cmd: list[str], label: str) -> None:
    print(f"[→] {label}...")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"[FAIL] {label} に失敗しました（終了コード {result.returncode}）")
        sys.exit(result.returncode)
    print(f"[OK] {label}")


run([sys.executable, "-m", "pip", "install", "playwright"], "playwright インストール")
run([sys.executable, "-m", "playwright", "install", "chromium"], "Chromium インストール")
print("\nPlaywright セットアップ完了")
print("次のコマンドでスクリーンショットを取得できます:")
print("  python scripts/dev_screenshot.py")
