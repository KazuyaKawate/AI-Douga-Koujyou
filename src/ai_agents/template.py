"""AgentTemplate — Agent 用プロンプトテンプレートレンダラー。

{variable} 形式の変数置換をサポート。
templates/ ディレクトリからテンプレートファイルを読み込める。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


class AgentTemplate:
    """
    シンプルなプロンプトテンプレート。

    記法:
        {variable}          — context dict の値で置換
        {variable:default}  — 値がなければ default を使用

    テンプレートファイル (.txt / .md) は templates/ ディレクトリから読み込む。
    """

    def __init__(self, template: str) -> None:
        self._template = template

    @classmethod
    def from_file(cls, path: Path) -> "AgentTemplate":
        return cls(path.read_text(encoding="utf-8"))

    @classmethod
    def from_factory_dir(
        cls,
        factory_dir: Path,
        template_name: str,
    ) -> Optional["AgentTemplate"]:
        """Factory の templates/ ディレクトリからテンプレートを読み込む。"""
        for ext in (".txt", ".md", ".j2"):
            candidate = factory_dir / "templates" / f"{template_name}{ext}"
            if candidate.exists():
                return cls.from_file(candidate)
        return None

    @property
    def raw(self) -> str:
        return self._template

    def render(self, context: dict) -> str:
        """context dict を使って {variable} を置換して返す。"""
        result = self._template

        def replacer(m: re.Match) -> str:
            inner   = m.group(1)
            if ":" in inner:
                key, default = inner.split(":", 1)
            else:
                key, default = inner, ""
            key = key.strip()
            val = context.get(key)
            if val is None:
                return default
            return str(val)

        result = re.sub(r"\{([^{}]+)\}", replacer, result)
        return result

    def variables(self) -> list[str]:
        """テンプレート内の変数名一覧を返す。"""
        matches = re.findall(r"\{([^{}]+)\}", self._template)
        result  = []
        for m in matches:
            key = m.split(":")[0].strip()
            if key not in result:
                result.append(key)
        return result

    def __repr__(self) -> str:
        preview = self._template[:60].replace("\n", "\\n")
        return f"AgentTemplate({preview!r}...)"
