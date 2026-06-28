from .base import BaseFactory


class VideoFactory(BaseFactory):
    """動画コンテンツ生成 Factory（スタブ）。"""

    @property
    def factory_name(self) -> str:
        return "video"
