"""StoreRegistry — インストール済みパッケージの管理・GUI 対応レジストリ。

from src.utils.json_store import save_json_atomic
永続化: data/store/registry.json
バージョン履歴: data/store/versions/{package_id}/v{version}.apagent
"""
from __future__ import annotations

import json
import shutil
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .manifest import PackageManifest

_REGISTRY_FILE  = Path("data/store/registry.json")
_PACKAGES_DIR   = Path("data/store/packages")
_VERSIONS_DIR   = Path("data/store/versions")

_lock:     threading.Lock         = threading.Lock()
_instance: Optional["StoreRegistry"] = None


@dataclass
class InstalledPackage:
    """インストール済みパッケージの記録。"""
    package_id:     str
    name:           str
    current_version: str
    agent_id:       str
    installed_at:   str
    updated_at:     str
    package_path:   str            # 現在インストール済みの .apagent のパス
    versions:       list[str]      = field(default_factory=list)
    tags:           list[str]      = field(default_factory=list)
    enabled:        bool           = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "InstalledPackage":
        return cls(
            package_id=d["package_id"],
            name=d.get("name", d["package_id"]),
            current_version=d.get("current_version", "1.0.0"),
            agent_id=d.get("agent_id", ""),
            installed_at=d.get("installed_at", ""),
            updated_at=d.get("updated_at", ""),
            package_path=d.get("package_path", ""),
            versions=list(d.get("versions", [])),
            tags=list(d.get("tags", [])),
            enabled=bool(d.get("enabled", True)),
        )


@dataclass
class InstallResult:
    success:      bool
    package_id:   str            = ""
    version:      str            = ""
    action:       str            = ""   # "installed" | "updated" | "skipped"
    warnings:     list[str]      = field(default_factory=list)
    error:        Optional[str]  = None

    def __str__(self) -> str:
        if self.success:
            return f"{self.action}: {self.package_id} v{self.version}"
        return f"FAIL: {self.error}"


class StoreRegistry:
    """
    GUI 対応の Agent Store レジストリ。

    機能:
        install(path)           — .apagent をインストール（Agent + Workflow + Template 即時登録）
        uninstall(package_id)   — アンインストール（AgentRegistry から削除）
        update(package_id, path)— 旧バージョンをバックアップしてアップデート
        rollback(package_id, v) — 指定バージョンにロールバック
        list_installed()        — インストール済み一覧（GUI 表示用）
        get_versions(id)        — バージョン履歴一覧
    """

    def __init__(self) -> None:
        self._data: dict[str, InstalledPackage] = {}
        self._load()

    # ---- Install / Uninstall ----------------------------------------

    def install(
        self,
        package_path: Path,
        overwrite:    bool = True,
    ) -> InstallResult:
        """
        .apagent をインストールする。

        1. AgentImporter でインポート（即時ロード）
        2. パッケージファイルを data/store/packages/ にコピー
        3. registry.json を更新
        """
        from .importer import AgentImporter
        imp_result = AgentImporter().import_package(package_path, overwrite=overwrite)

        if not imp_result.success:
            return InstallResult(success=False, error=imp_result.error)

        manifest = imp_result.manifest
        pkg_id   = manifest.package_id
        now      = datetime.now().isoformat(timespec="seconds")

        # .apagent を packages/ にコピー保存
        _PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
        dest = _PACKAGES_DIR / manifest.package_filename()
        shutil.copy2(package_path, dest)

        action = "updated" if pkg_id in self._data else "installed"

        # 旧バージョンをバックアップ
        if pkg_id in self._data:
            self._backup_version(pkg_id, self._data[pkg_id].current_version,
                                 Path(self._data[pkg_id].package_path))

        installed = InstalledPackage(
            package_id      = pkg_id,
            name            = manifest.name,
            current_version = manifest.version,
            agent_id        = manifest.agent_id,
            installed_at    = self._data[pkg_id].installed_at if pkg_id in self._data else now,
            updated_at      = now,
            package_path    = str(dest),
            versions        = self._get_available_versions(pkg_id, manifest.version),
            tags            = list(manifest.tags),
            enabled         = True,
        )
        self._data[pkg_id] = installed
        self._save()

        return InstallResult(
            success=True,
            package_id=pkg_id,
            version=manifest.version,
            action=action,
            warnings=imp_result.warnings,
        )

    def uninstall(self, package_id: str) -> bool:
        """パッケージをアンインストールする（AgentRegistry から Agent を削除）。"""
        pkg = self._data.get(package_id)
        if pkg is None:
            return False

        try:
            from src.ai_agents.registry import get_agent_registry
            get_agent_registry().delete(pkg.agent_id)
        except Exception:
            pass

        del self._data[package_id]
        self._save()
        return True

    # ---- Update / Rollback ------------------------------------------

    def update(self, package_id: str, new_package_path: Path) -> InstallResult:
        """旧バージョンを保存してから新バージョンをインストールする。"""
        if package_id not in self._data:
            return self.install(new_package_path)
        return self.install(new_package_path, overwrite=True)

    def rollback(self, package_id: str, version: str) -> InstallResult:
        """指定バージョンの .apagent を復元してインストールする。"""
        ver_path = _VERSIONS_DIR / package_id / f"v{version}.apagent"
        if not ver_path.exists():
            return InstallResult(
                success=False, error=f"Version {version!r} not found in history"
            )
        return self.install(ver_path, overwrite=True)

    # ---- Query (GUI 対応) -------------------------------------------

    def list_installed(self, enabled_only: bool = False) -> list[InstalledPackage]:
        pkgs = list(self._data.values())
        if enabled_only:
            pkgs = [p for p in pkgs if p.enabled]
        return sorted(pkgs, key=lambda p: p.package_id)

    def get_installed(self, package_id: str) -> Optional[InstalledPackage]:
        return self._data.get(package_id)

    def get_versions(self, package_id: str) -> list[str]:
        ver_dir = _VERSIONS_DIR / package_id
        if not ver_dir.exists():
            return []
        return sorted(
            [p.stem[1:] for p in ver_dir.glob("v*.apagent")],
            reverse=True,
        )

    def count(self) -> int:
        return len(self._data)

    def exists(self, package_id: str) -> bool:
        return package_id in self._data

    # ---- Persistence ------------------------------------------------

    def _load(self) -> None:
        if not _REGISTRY_FILE.exists():
            return
        try:
            raw = json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))
            for pid, d in raw.get("installed", {}).items():
                self._data[pid] = InstalledPackage.from_dict(d)
        except Exception:
            pass

    def _save(self) -> None:
        _REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"installed": {pid: pkg.to_dict() for pid, pkg in self._data.items()}}
        save_json_atomic(_REGISTRY_FILE, data)

    # ---- Private ----------------------------------------------------

    def _backup_version(self, package_id: str, version: str, src: Path) -> None:
        if not src.exists():
            return
        ver_dir = _VERSIONS_DIR / package_id
        ver_dir.mkdir(parents=True, exist_ok=True)
        dest = ver_dir / f"v{version}.apagent"
        if not dest.exists():
            shutil.copy2(src, dest)

    def _get_available_versions(self, package_id: str, current: str) -> list[str]:
        versions = self.get_versions(package_id)
        if current not in versions:
            versions.insert(0, current)
        return sorted(set(versions), reverse=True)


# ---- Singleton -------------------------------------------------------

def get_store_registry() -> StoreRegistry:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = StoreRegistry()
    return _instance


def reset_store_registry() -> None:
    global _instance
    with _lock:
        _instance = None
