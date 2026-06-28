from .base import BaseTrigger
from .interval import IntervalTrigger
from .cron import CronTrigger
from .webhook import WebhookTrigger
from .manual import ManualTrigger
from .startup import StartupTrigger
from .calendar import CalendarTrigger

# トリガー識別子 → クラスのレジストリ。新規トリガー追加時はここに登録する。
TRIGGER_REGISTRY: dict[str, type[BaseTrigger]] = {
    "interval": IntervalTrigger,
    "cron":     CronTrigger,
    "webhook":  WebhookTrigger,
    "manual":   ManualTrigger,
    "startup":  StartupTrigger,
    "calendar": CalendarTrigger,
}

__all__ = [
    "BaseTrigger",
    "IntervalTrigger",
    "CronTrigger",
    "WebhookTrigger",
    "ManualTrigger",
    "StartupTrigger",
    "CalendarTrigger",
    "TRIGGER_REGISTRY",
]
