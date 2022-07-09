from monitoring.log import LogWindow
from datetime import datetime, timedelta
from monitoring.errors import TimeLineError
from collections import deque
from typing import Deque

class TimeLine:
    """Class encapsulates the timeline equal to the size `window_size` and contains list of the request per sec(RPS)
        Example: 
            1:00 - 10 requests
            1:01 - 5 requests
            1:02 - 4 requests

        Then we can merge logs to get 1-minutes lists, and merge 1-minutes list to get 5-minutes list and etc...
    """

    def __init__(self, window_size: timedelta) -> None:
        self.queue: Deque[LogWindow] = deque()
        self.window_size = window_size

    def pop_left(self, current_time: datetime):
        while self.queue and self.queue[0].time <= current_time:
            self.queue.popleft()

    def append(self, log_window: LogWindow):
        """log_window 1 sec interval stores the number of requests per sec"""
        if not log_window:
            raise TimeLineError("Can't create time line with empty logs")

        if not self.queue:
            self.queue.append(log_window)
            return

        # Extend the current timeline. if prev time = 1:01 and current_time = 1:10
        # set the RPS in the range [02-09] equal 0
        next_time = self.queue[-1].time + timedelta(seconds=1)
        while next_time < log_window.time:
            self.queue.append(LogWindow(next_time))
            next_time += timedelta(seconds=1)

        self.queue.append(log_window)
