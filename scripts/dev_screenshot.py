"""開発確認用スクリーンショット取得ツール。
本番コードには組み込まない。import もしない。

使い方:
  1. Streamlit を起動: python -m streamlit run app.py
  2. このスクリプトを実行: python scripts/dev_screenshot.py
  3. screenshots/dev/ に保存される

オプション:
  --headed  : ブラウザを表示する（デフォルト: headless）
  --url URL : Streamlit URL（デフォルト: http://localhost:8501）
"""
import argparse
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    from playwright.async_api import TimeoutError as PWTimeout
except ImportError:
    print("[ERROR] Playwright が未インストールです。")
    print("  インストール方法: python scripts/install_playwright.py")
    sys.exit(1)

SAVE_DIR = Path("screenshots/dev")
TIMEOUT  = 20_000  # ms
TAB_NAME = "Workspace Sync"


async def _wait_streamlit(page):
    """Streamlit のメインコンテナが表示されるまで待機。"""
    await page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=TIMEOUT)
    await page.wait_for_timeout(1200)


async def _click_workspace_sync_tab(page):
    """Tab 10 (🔄 Workspace Sync) をクリックして表示を待つ。"""
    tab = page.get_by_role("tab", name=re.compile(TAB_NAME))
    await tab.wait_for(state="visible", timeout=TIMEOUT)
    await tab.click()
    # モード切り替えラジオが現れるまで待つ（Tab 10 のレンダリング完了の目印）
    await page.wait_for_selector('[data-testid="stRadio"]', timeout=TIMEOUT)
    await page.wait_for_timeout(1000)


async def _switch_mode(page, label: str):
    """初心者モード / 詳細モード を切り替える。"""
    radio_label = page.locator('[data-testid="stRadio"] label').filter(
        has_text=label
    ).first
    await radio_label.wait_for(state="visible", timeout=TIMEOUT)
    await radio_label.click()
    await page.wait_for_timeout(1200)


async def capture(headed: bool = False, base_url: str = "http://localhost:8501"):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not headed)
        page    = await browser.new_page(
            viewport={"width": 1280, "height": 900}
        )

        try:
            # Development Studio へ直接移動
            print(f"[→] {base_url}/Development_Studio を開いています...")
            await page.goto(
                f"{base_url}/Development_Studio",
                wait_until="domcontentloaded",
            )
            await _wait_streamlit(page)
            print("[OK] Development Studio 表示")

            # Tab 10 をクリック
            await _click_workspace_sync_tab(page)
            print("[OK] Workspace Sync タブ表示")

            # ── Beginner Mode キャプチャ ────────────────────────────
            # デフォルトで初心者モードのはずだが明示的に切り替え
            await _switch_mode(page, "初心者モード")
            path_beginner = SAVE_DIR / f"beginner_{ts}.png"
            await page.screenshot(path=str(path_beginner), full_page=False)
            print(f"[OK] Beginner Mode 保存: {path_beginner}")

            # ── Advanced Mode キャプチャ ─────────────────────────────
            await _switch_mode(page, "詳細モード")
            path_advanced = SAVE_DIR / f"advanced_{ts}.png"
            await page.screenshot(path=str(path_advanced), full_page=False)
            print(f"[OK] Advanced Mode 保存: {path_advanced}")

            # ── Tab 全体フルページキャプチャ（Beginner Mode に戻す）─
            await _switch_mode(page, "初心者モード")
            path_full = SAVE_DIR / f"tab10_full_{ts}.png"
            await page.screenshot(path=str(path_full), full_page=True)
            print(f"[OK] フルページ 保存:    {path_full}")

        except PWTimeout as exc:
            print(f"[ERROR] タイムアウト: {exc}")
            print("Streamlit が起動しているか確認してください:")
            print("  python -m streamlit run app.py")
            await page.screenshot(
                path=str(SAVE_DIR / f"error_{ts}.png"), full_page=False
            )
            sys.exit(1)

        finally:
            await browser.close()

    print(f"\n保存先: {SAVE_DIR.resolve()}")
    print("完了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Development Studio スクリーンショット取得（開発確認専用）"
    )
    parser.add_argument(
        "--headed", action="store_true", help="ブラウザを画面表示する"
    )
    parser.add_argument(
        "--url", default="http://localhost:8501", help="Streamlit URL"
    )
    args = parser.parse_args()
    asyncio.run(capture(headed=args.headed, base_url=args.url))
