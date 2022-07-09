import csv
from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from time import sleep
from typing import List, Optional
import logging

from monitoring.log import Log, LogWindow
from monitoring.timeline import TimeLine
from itertools import groupby
from rich.console import Console
from rich.table import Table
from typing import Any

console = Console()

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    hits: int
    total_bytes: int
    errors: int
    error_percentage: int
    top_k: List[Any]
    start_time: datetime
    end_time: datetime


@dataclass
class SectionStat:
    name: str
    hits: int
    logs: List[Log]


@dataclass
class Alert:
    rps: int
    created_at: datetime
    shown: bool = False
    recover_at: Optional[datetime] = None


class AbstractNotification(ABC):
    def __init__(self, window_size: timedelta) -> None:
        if int(window_size.total_seconds()) < 1:
            raise ValueError('Invalid window size')
        self.window_size = window_size
        self.timeline = TimeLine(window_size)

    @abstractmethod
    def update(self, window: LogWindow) -> None:
        """Update timeline for the current interval"""
        raise NotImplemented("This method should be overridden")

    @abstractmethod
    def clear_notification(self):
        raise NotImplemented("This method should be overridden")

    def group_by_section(self):
        fn = lambda log: log.section_name
        queue = self.timeline.queue
        log_list = []
        for x in queue:
            log_list.extend([xx for xx in x.items])
        sorted_list = sorted(log_list, key=lambda log: log.section_name)
        sorted_list = {k: list(v) for k, v in groupby(sorted_list, key=fn)}
        return [SectionStat(name=name, hits=len(logs), logs=logs) for name, logs in sorted_list.items()]

    def top_k(self, limit: int):
        sections = self.group_by_section()
        return sorted(sections, key=lambda x: x.hits, reverse=True)[:limit]


class SummaryNotification(AbstractNotification):
    def __init__(self, window_size: timedelta) -> None:
        super().__init__(window_size)
        self.notification = None

    @property
    def has_notification(self):
        return self.notification is not None

    def clear_notification(self):
        self.notification = None

    def update(self, window: LogWindow) -> None:
        queue = self.timeline.queue
        if queue and window.time - queue[0].time > self.window_size:
            self.update_stats()
            self.timeline.pop_left(window.time)
        self.timeline.append(window)

    def update_stats(self):
        queue = self.timeline.queue
        if not queue:
            return
        log_list = []
        for x in queue:
            log_list.extend(x.items)

        hits = len(log_list)
        total_bytes = sum([log.bytes for log in log_list])
        errors = len([log for log in log_list if log.has_error])
        error_percentage = 0 if not hits else round((errors / hits) * 100, 2)
        start_time = log_list[0].time
        end_time = start_time + self.window_size
        self.notification = Summary(hits=len(log_list),
                                    total_bytes=total_bytes,
                                    errors=errors,
                                    error_percentage=error_percentage,
                                    top_k=self.top_k(10),
                                    start_time=start_time,
                                    end_time=end_time)


class AlertNotification(AbstractNotification):
    def __init__(self, window_size: timedelta, threshold: int = 10) -> None:
        super().__init__(window_size)
        self.errors: List[Alert] = []
        self.threshold = threshold

    def update(self, window: Optional[LogWindow]) -> None:
        queue = self.timeline.queue
        if queue and window.time - queue[0].time > self.window_size:
            self.update_stats()
            self.timeline.pop_left(window.time)
        self.timeline.append(window)

    @property
    def has_notification(self):
        return len(self.errors) > 0

    @property
    def active_error(self):
        if self.errors and self.errors[-1].recover_at is None:
            return self.errors[-1]

    def clear_notification(self):
        if self.has_notification:
            error = self.errors[-1]
            if error.recover_at is not None:
                self.errors.pop()
            else:
                error.shown = True

    def update_stats(self):
        queue = self.timeline.queue
        if not queue:
            return
        seconds = int(self.window_size.total_seconds())
        rps = round(sum([len(x.items) for x in queue]) / seconds, 2)
        active_error = self.active_error
        # if process recovered
        if rps < self.threshold:
            if active_error:
                self.errors[-1].recover_at = datetime.now()
            return
        # create new error
        if not active_error:
            self.errors.append(Alert(rps=rps, created_at=datetime.now()))


class Monitoring:
    def __init__(
        self,
        file_path: str,
        rps: int,
        summary_window_time: timedelta,
        alert_window_time: timedelta,
        hide_alert_notify: bool,
        hide_summary_notify: bool,
        ui_time_tick: int,
    ) -> None:
        self.file_path = file_path
        self.ui_time_tick = ui_time_tick
        self.hide_summary_notify = hide_summary_notify
        self.hide_alert_notify = hide_alert_notify
        self.summary = SummaryNotification(summary_window_time)
        self.alert = AlertNotification(alert_window_time, threshold=rps)

    def create_stream(self, file_path: str):
        if not file_path:
            raise ValueError('Specify the path to the file')
        with open(file_path, mode='r') as textfile:
            textfile.readline()  # skip headers
            for row in csv.reader(textfile):
                yield Log.parse(row)

    def run(self) -> None:
        try:
            it = Log.process_log(self.file_path)
            while True:
                # window - contains the RPS
                window = next(it)
                logger.debug((window.time, len(window.items)))
                self.update_terminal(window)
                # timeout(blocking operation)
                sleep(self.ui_time_tick)                
        except KeyboardInterrupt:
            print('Monitoring has been stopped!')

    def update_terminal(self, window) -> None:
        # received new logs need to update the summary and alert stats
        self.summary.update(window)
        self.alert.update(window)
        summary = self.summary
        alert = self.alert
        if summary.has_notification and not self.hide_summary_notify:
            self.display_summary(summary.notification)
            self.summary.clear_notification()

        if alert.has_notification and not self.hide_alert_notify:
            self.display_alerts(alert)
            self.alert.clear_notification()

    @staticmethod
    def display_summary(summary: Summary) -> None:
        console.print('=================================Statistics=================================')
        table = Table(title="Summary summary")
        table.add_column("Hits", style="bold green")
        table.add_column("Bytes", style="bold green")
        table.add_column("Start Time", header_style="bold green")
        table.add_column("End Time", header_style="bold green")
        table.add_column("Errors", header_style="bold red")
        table.add_column("Error %", header_style="bold red")

        table.add_row(str(summary.hits), str(summary.total_bytes), str(summary.start_time), str(summary.end_time),
                      str(summary.errors), str(summary.error_percentage))
        console.print(table)

        table = Table(title="Top 10 section by hit rate")
        table.add_column("Name", style="magenta")
        table.add_column("Hit rate", style="magenta")
        for x in summary.top_k:
            table.add_row(x.name, str(x.hits))
        console.print(table)

    @staticmethod
    def display_alerts(alert: AlertNotification) -> None:
        error = alert.errors[-1]
        if error.recover_at is not None:
            recover_time = error.recover_at - error.created_at
            console.print(f"Traffic recovered after {recover_time}")
        elif not error.shown:
            rps = error.rps
            created_at = error.created_at.strftime("%Y-%m-%d %H:%M:%S %Z")
            console.print(f"High traffic generated an alert - hits = {rps} triggered at {created_at}")
