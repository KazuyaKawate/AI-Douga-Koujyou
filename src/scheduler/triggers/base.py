from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime


class BaseTrigger(ABC):
    """
    スケジューラートリガーの基底インターフェース。

    新しいトリガーを追加する手順:
        1. このクラスを継承したクラスを triggers/ 以下に作成する
        2. 抽象メソッドをすべて実装する
        3. triggers/__init__.py の TRIGGER_REGISTRY に登録する

    FactoryScheduler はこのインターフェースのみに依存する。
    「いつ発火するか」はサブクラスに閉じること。

    将来追加予定:
        CronTrigger     - Cron 式でスケジューリング
        WebhookTrigger  - 外部 Webhook を受信して発火
        ManualTrigger   - 外部コードから fire() を呼んで発火
        StartupTrigger  - 起動時に一度だけ発火
        CalendarTrigger - カレンダーベースのスケジューリング
    """

    @property
    @abstractmethod
    def trigger_name(self) -> str:
        """トリガー識別子（例: "interval", "cron"）。SchedulerStatus に記録される。"""
        ...

    @abstractmethod
    def should_fire(self) -> bool:
        """
        このトリガーが発火すべき状態かを返す。

        True を返すと FactoryScheduler が _tick() を実行する。
        この呼び出し自体はトリガーの内部状態を変更しない。
        状態の更新は on_fired() で行う。
        """
        ...

    @abstractmethod
    def on_fired(self) -> None:
        """
        _tick() 完了後に呼ばれる。

        IntervalTrigger は last_fired_at を更新する。
        CronTrigger は次の発火時刻を計算する。
        状態をリセットして次回の should_fire() 判定に備える。
        """
        ...

    @abstractmethod
    def next_fire_at(self) -> datetime | None:
        """
        次回発火予定時刻を返す。

        不確定な場合（ManualTrigger など）は None を返す。
        SchedulerStatus.next_scheduled_at に記録される。
        """
        ...

    def time_until_fire(self) -> float:
        """
        次回発火まで何秒かを返す。デフォルト実装は next_fire_at() から算出。

        負値なら即座に発火すべき。
        FactoryScheduler がスリープ時間を決定するために使う。
        サブクラスでオーバーライドしてより精密な値を返せる。
        """
        nf = self.next_fire_at()
        if nf is None:
            return 0.0
        return max((nf - datetime.now()).total_seconds(), 0.0)
