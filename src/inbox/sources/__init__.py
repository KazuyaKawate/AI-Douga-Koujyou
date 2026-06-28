from .base import BaseInboxSource
from .sheets import GoogleSheetsInboxSource
from .chatgpt import ChatGPTInboxSource
from .line import LINEInboxSource
from .chatwork import ChatworkInboxSource
from .discord import DiscordInboxSource
from .slack import SlackInboxSource
from .rest_api import RESTAPIInboxSource

# ソース識別子 → クラスのレジストリ。新規ソース追加時はここに登録する。
SOURCE_REGISTRY: dict[str, type[BaseInboxSource]] = {
    "google_sheets": GoogleSheetsInboxSource,
    "chatgpt":       ChatGPTInboxSource,
    "line":          LINEInboxSource,
    "chatwork":      ChatworkInboxSource,
    "discord":       DiscordInboxSource,
    "slack":         SlackInboxSource,
    "rest_api":      RESTAPIInboxSource,
}

__all__ = [
    "BaseInboxSource",
    "GoogleSheetsInboxSource",
    "ChatGPTInboxSource",
    "LINEInboxSource",
    "ChatworkInboxSource",
    "DiscordInboxSource",
    "SlackInboxSource",
    "RESTAPIInboxSource",
    "SOURCE_REGISTRY",
]
