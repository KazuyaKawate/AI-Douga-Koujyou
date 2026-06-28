from .base import BaseFactory


class SNSFactory(BaseFactory):
    """SNS 投稿コンテンツ生成 Factory（スタブ）。"""

    @property
    def factory_name(self) -> str:
        return "sns"
