from .base import BaseFactory


class MarketingFactory(BaseFactory):
    """マーケティング・広告コンテンツ生成 Factory（スタブ）。"""

    @property
    def factory_name(self) -> str:
        return "marketing"
