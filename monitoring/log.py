from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep
from typing import List
from monitoring.errors import LogWindowError
import logging
import csv

LOG_HEADERS = ['remotehost', 'rfc931', 'authuser', 'time', 'api', 'status', 'bytes']
"""
Example log file (first line is the header):
"remotehost","rfc931","authuser","date","request","status","bytes"
"10.0.0.1","-","apache",1549574332,"GET /api/user HTTP/1.0",200,1234
"10.0.0.4","-","apache",1549574333,"GET /report HTTP/1.0",200,1136
"10.0.0.1","-","apache",1549574334,"GET /api/user HTTP/1.0",200,1194
"""

LOGGER = logging.getLogger(__name__)


@dataclass
class Log:
    remotehost: str
    rfc931: str
    authuser: str
    time: datetime
    method: str
    api_url: str
    http_version: str
    status: int
    bytes: int

    @classmethod
    def parse(self, log: List):
        if log is None:
            return None
        mapping = {}
        for k, v in zip(LOG_HEADERS, log):
            if k == 'time':
                mapping[k] = datetime.fromtimestamp(int(v))
            elif k in ['bytes', 'status']:
                mapping[k] = int(v)
            elif k == 'api':
                for kk, vv in zip(['method', 'api_url', 'http_version'], v.split(' ')):
                    mapping[kk] = vv
            else:
                mapping[k] = v
        return self(**mapping)

    @property
    # A section is defined as being what's before the second '/' in the resource section of the log line.
    def section_name(self):
        path = [c for c in self.api_url.split("/") if c]
        return f"/{path[0]}" if path else "/"

    @property
    def has_error(self):
        client_error = 400 <= self.status <= 451
        server_error = 500 <= self.status <= 511
        return client_error or server_error

    @staticmethod
    def process_log(file_path: str, waiting_time: int = None):
        window = None
        processing_start_time = datetime.now()
        with open(file_path, mode='r') as textfile:
            textfile.readline()  # skip headers
            gen = csv.reader(textfile)
            while True:
                try:
                    row = next(gen)
                    if not row:
                        continue
                    log_record: Log = Log.parse(row)
                    # need to create a new window
                    if window and log_record.time != window.time:
                        yield window
                        window = None
                    if window is None:
                        window = LogWindow(log_record.time)
                    window.push(log_record)
                except StopIteration:
                    if waiting_time is not None and datetime.now() - processing_start_time > timedelta(seconds=waiting_time):
                        return
                    sleep(1.0)

class LogWindow:
    def __init__(self, time: datetime) -> None:
        self.time = time
        self.items: List[Log] = []

    def push(self, log: Log):
        if log.time != self.time:
            raise LogWindowError("Adding error, need to create a new window log")
        self.items.append(log)
