from .base import BaseFactory


class WritingFactory(BaseFactory):
    """文章・記事生成 Factory（スタブ）。"""

    @property
    def factory_name(self) -> str:
        return "writing"
