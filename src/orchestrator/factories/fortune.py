from .base import BaseFactory


class FortuneFactory(BaseFactory):
    """占い・運勢コンテンツ生成 Factory（スタブ）。"""

    @property
    def factory_name(self) -> str:
        return "fortune"
