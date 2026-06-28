from .base import BaseFactory


class CreatorFactory(BaseFactory):
    """クリエイター系コンテンツ生成 Factory（スタブ）。"""

    @property
    def factory_name(self) -> str:
        return "creator"
