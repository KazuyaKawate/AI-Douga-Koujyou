"""AIOS Agent Store — パッケージ管理・Marketplace システム。

基本的な使い方:
    # エクスポート
    from src.agent_store import AgentExporter
    result = AgentExporter().export("writing_specialist", author="Me")

    # インポート
    from src.agent_store import AgentImporter
    result = AgentImporter().import_package(Path("output/store/writing_specialist_pkg_v1_0_0.apagent"))

    # Store 管理
    from src.agent_store import get_store_registry
    store = get_store_registry()
    store.install(Path("output/store/xxx.apagent"))
    store.list_installed()
    store.rollback("writing_specialist_pkg", "1.0.0")

    # Marketplace
    from src.agent_store import MarketplaceProvider
    mp = MarketplaceProvider()
    mp.search("writing")
    mp.get_featured()
"""
from .manifest        import PackageManifest
from .exporter        import AgentExporter, ExportResult
from .importer        import AgentImporter, ImportResult
from .store_registry  import StoreRegistry, InstalledPackage, InstallResult, get_store_registry, reset_store_registry
from .marketplace     import MarketplaceProvider, MarketplaceItem

__all__ = [
    "PackageManifest",
    "AgentExporter",
    "ExportResult",
    "AgentImporter",
    "ImportResult",
    "StoreRegistry",
    "InstalledPackage",
    "InstallResult",
    "get_store_registry",
    "reset_store_registry",
    "MarketplaceProvider",
    "MarketplaceItem",
]
