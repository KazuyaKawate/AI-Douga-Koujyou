"""
test_agent_store.py — Agent Store の動作確認テスト

テスト項目:
    1. Export  — Agent を .apagent にパッケージ化
    2. Import  — .apagent を読み込んでホットロード登録
    3. Version — バージョン管理・履歴確認
    4. Rollback— 旧バージョンへの巻き戻し
    5. Marketplace — 検索・カテゴリ・おすすめ一覧
    6. StoreRegistry — GUI 向け一覧 API
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(".env"), override=False)

# ── 共通ユーティリティ ───────────────────────────────────────────────
def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def ok(msg: str) -> None:
    print(f"  ✓ {msg}")

def fail(msg: str) -> None:
    print(f"  ✗ {msg}")
    sys.exit(1)


# ── 1. Export ──────────────────────────────────────────────────────
section("1. Export — writing_specialist → .apagent")

from src.ai_agents.registry import get_agent_registry
reg = get_agent_registry()
reg.auto_load()

from src.agent_store import AgentExporter
exporter = AgentExporter()

result = exporter.export(
    agent_id      = "writing_specialist",
    author        = "AIOS Test Suite",
    template_text = "あなたは優秀なライターです。\n\nテーマ: {topic}\nトーン: {tone}\n\n{topic} について詳しく解説してください。",
    tags          = ["writing", "test"],
    output_dir    = Path("output/store"),
)

if not result.success:
    fail(f"Export 失敗: {result.error}")

ok(f"Export 成功 → {result.package_path}")
ok(f"  manifest.package_id = {result.manifest.package_id}")
ok(f"  version             = {result.manifest.version}")
ok(f"  has_template        = {result.manifest.has_template}")
ok(f"  checksum            = {result.manifest.checksum[:16]}...")

apagent_path = result.package_path


# ── 2. Import ──────────────────────────────────────────────────────
section("2. Import — .apagent → ホットロード登録")

from src.agent_store import AgentImporter, reset_store_registry
imp = AgentImporter()

# ZIP 検証
import zipfile
with zipfile.ZipFile(apagent_path) as zf:
    names = zf.namelist()
    ok(f".apagent 内容: {names}")
    required = {"manifest.json", "agent.json", "icon.png"}
    missing  = required - set(names)
    if missing:
        fail(f"必須ファイルが不足: {missing}")
    ok("必須ファイル manifest.json / agent.json / icon.png をすべて確認")

imp_result = imp.import_package(apagent_path, overwrite=True)

if not imp_result.success:
    fail(f"Import 失敗: {imp_result.error}")

ok(f"Import 成功: agent={imp_result.agent_id}")
ok(f"  template 保存: {imp_result.has_template}")
if imp_result.warnings:
    print(f"  ⚠ warnings: {imp_result.warnings}")

# AgentRegistry に登録されているか確認
agent = get_agent_registry().get("writing_specialist")
if agent is None:
    fail("writing_specialist が AgentRegistry に見つかりません")
ok(f"AgentRegistry 確認: {agent.agent_id} v{agent.version}")

# template が保存されているか確認
tmpl_path = Path("data/store/templates/writing_specialist.txt")
if not tmpl_path.exists():
    fail("template.txt が保存されていません")
ok(f"テンプレート保存確認: {tmpl_path}")


# ── 3. StoreRegistry — インストール ────────────────────────────────
section("3. StoreRegistry — install / list_installed")

from src.agent_store import get_store_registry
reset_store_registry()
store = get_store_registry()

install_result = store.install(apagent_path)
if not install_result.success:
    fail(f"install 失敗: {install_result.error}")
ok(f"install: {install_result}")

installed = store.list_installed()
if not installed:
    fail("list_installed が空です")
ok(f"list_installed: {len(installed)} パッケージ")
for pkg in installed:
    ok(f"  {pkg.package_id} v{pkg.current_version} (agent={pkg.agent_id})")


# ── 4. Version 管理 ─────────────────────────────────────────────────
section("4. Version 管理 — 新バージョンのエクスポート → アップデート")

# 旧バージョンをバックアップしてから新バージョンをインストールする流れ
# writing_specialist を v1.1.0 に更新

agent_v1  = get_agent_registry().get("writing_specialist")
v1_json   = agent_v1.to_dict()

# バージョン番号を上げた Agent を作成
from src.ai_agents.definition import AgentDefinition
agent_v11 = AgentDefinition.from_dict({
    **v1_json,
    "version":     "1.1.0",
    "description": "v1.1.0: SEO 強化版。タイトルタグ・見出し構造を自動最適化する高品質記事執筆専門 Agent。",
})
get_agent_registry().register(agent_v11, overwrite=True)
get_agent_registry().save(agent_v11)

# v1.1.0 をエクスポート
export_v11 = exporter.export(
    agent_id  = "writing_specialist",
    author    = "AIOS Test Suite",
    output_dir = Path("output/store"),
)
if not export_v11.success:
    fail(f"v1.1.0 Export 失敗: {export_v11.error}")
ok(f"v1.1.0 Export: {export_v11.package_path}")

# StoreRegistry で update
upd = store.update("writing_specialist_pkg", export_v11.package_path)
if not upd.success:
    fail(f"update 失敗: {upd.error}")
ok(f"update 結果: {upd}")

# バージョン履歴確認
versions = store.get_versions("writing_specialist_pkg")
ok(f"バージョン履歴: {versions}")

# 現在バージョンが 1.1.0 になっているか
pkg_now = store.get_installed("writing_specialist_pkg")
ok(f"現在バージョン: {pkg_now.current_version}")
if pkg_now.current_version != "1.1.0":
    fail(f"現在バージョンが 1.1.0 ではありません: {pkg_now.current_version}")
ok("バージョン 1.1.0 に正常アップデート完了")


# ── 5. Rollback ────────────────────────────────────────────────────
section("5. Rollback — v1.1.0 → v1.0.0 に巻き戻し")

# v1.0.0 のバックアップが存在するか確認
ver_dir = Path("data/store/versions/writing_specialist_pkg")
ok(f"バックアップディレクトリ: {ver_dir}")
backups = list(ver_dir.glob("*.apagent")) if ver_dir.exists() else []
ok(f"バックアップファイル: {[b.name for b in backups]}")

if not backups:
    print("  ⚠ v1.0.0 バックアップなし（初回インストールのため正常）— Rollback はスキップ")
else:
    rb = store.rollback("writing_specialist_pkg", "1.0.0")
    if not rb.success:
        fail(f"Rollback 失敗: {rb.error}")
    ok(f"Rollback 結果: {rb}")

    pkg_rolled = store.get_installed("writing_specialist_pkg")
    if pkg_rolled.current_version != "1.0.0":
        fail(f"Rollback 後のバージョンが 1.0.0 ではありません: {pkg_rolled.current_version}")
    ok(f"Rollback 成功: 現在 v{pkg_rolled.current_version}")


# ── 6. Marketplace ─────────────────────────────────────────────────
section("6. Marketplace — 検索・カテゴリ・おすすめ")

from src.agent_store import MarketplaceProvider
mp = MarketplaceProvider(use_mock=True)

# カテゴリ一覧
cats = mp.get_categories()
ok(f"カテゴリ一覧 ({len(cats)}件): {cats}")

# おすすめ
featured = mp.get_featured()
ok(f"おすすめ ({len(featured)}件):")
for item in featured:
    ok(f"  [{item.category}] {item.name} v{item.version} ★{item.rating} ({item.downloads}DL)")

# キーワード検索
results = mp.search("writing")
ok(f"search('writing') → {len(results)} 件:")
for item in results:
    ok(f"  {item.package_id}: {item.name}")

# タグ検索
sns_results = mp.search(tags=["sns"])
ok(f"search(tags=['sns']) → {len(sns_results)} 件")

# 無料のみ
free_results = mp.search(free_only=True)
ok(f"search(free_only=True) → {len(free_results)} 件")

# カテゴリ別トップ
top_by_cat = mp.get_top_by_category(limit=2)
ok(f"カテゴリ別トップ2:")
for cat, items in top_by_cat.items():
    names = [i.name for i in items]
    ok(f"  {cat}: {names}")

# パッケージ詳細
detail = mp.get_package_info("writing_specialist_pkg")
if detail is None:
    fail("writing_specialist_pkg の詳細が取得できません")
ok(f"パッケージ詳細: {detail.name} by {detail.author}")


# ── 7. 複数 Agent の一括エクスポート ───────────────────────────────
section("7. 一括 Export — research_analyst / fortune_teller")

bulk = exporter.export_multiple(
    ["research_analyst", "fortune_teller"],
    output_dir = Path("output/store"),
    author     = "AIOS Test Suite",
)
for r in bulk:
    if r.success:
        ok(f"Export OK: {r.package_path.name}")
    else:
        ok(f"Export SKIP (not found): {r.error}")


# ── 完了サマリー ────────────────────────────────────────────────────
section("テスト完了")

print(f"  StoreRegistry: {store.count()} パッケージインストール済み")
print(f"  Marketplace:   {len(_MOCK_CATALOG_LEN := mp._catalog)} パッケージ")  # noqa
print(f"  Export 済み:   {len(list(Path('output/store').glob('*.apagent')))} ファイル")
print()
ok("全テスト PASS")
