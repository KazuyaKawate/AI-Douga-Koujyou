from .base import BaseFactory


class ResearchFactory(BaseFactory):
    """リサーチ・情報収集 Factory（スタブ）。"""

    @property
    def factory_name(self) -> str:
        return "research"
