from datetime import datetime
from monitoring.log import Log
import logging

LOGGER = logging.getLogger(__name__)


def default_log():
    return Log.parse(["-", "-", "-", 1549574332, "GET / HTTP/1.0", 200, 0])


def test_parsing():
    row = ["10.0.0.1", "-", "apache", 1549574332, "GET /api/user HTTP/1.0", 200, 1234]
    log: Log = Log.parse(row)
    assert log.remotehost == "10.0.0.1"
    assert log.rfc931 == "-"
    assert log.authuser == "apache"
    assert log.time == datetime(2019, 2, 8, 0, 18, 52)
    assert log.method == "GET"
    assert log.api_url == "/api/user"
    assert log.http_version == "HTTP/1.0"
    assert log.status == 200
    assert log.bytes == 1234


def test_parsing_section_name():
    log = default_log()

    log.api_url = "/api/user"
    assert log.section_name == "/api"

    log.api_url = "/api"
    assert log.section_name == "/api"

    log.api_url = "/"
    assert log.section_name == "/"


def test_parsing_error_status():
    log = default_log()

    log.status = 203
    assert log.has_error == False

    log.status = 200
    assert log.has_error == False

    log.status = 401
    assert log.has_error == True

    log.status = 500
    assert log.has_error == True