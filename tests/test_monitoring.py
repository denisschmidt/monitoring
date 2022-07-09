from datetime import timedelta
from monitoring.log import Log
from monitoring.monitoring import Monitoring
import logging


LOGGER = logging.getLogger(__name__)


def test_monitoring_log_sequence():
    it = Log.process_log('./tests/mock.csv', waiting_time=2)
    window = next(it)
    assert len(window.items) == 3
    window = next(it)
    assert len(window.items) == 2    
    window = next(it)
    assert len(window.items) == 2

def test_monitoring_summary():
    monitoring = Monitoring(
        file_path='',
        rps=3,
        summary_window_time=timedelta(seconds=10),
        alert_window_time=timedelta(seconds=30),
        ui_time_tick=0,
        hide_summary_notify=True,
        hide_alert_notify=True,
    )

    it = Log.process_log('./tests/mock.csv', waiting_time=2)
    window = next(it)
    monitoring.summary.update(window)
    assert len(window.items) == 3

    window = next(it)
    monitoring.summary.update(window)
    assert len(window.items) == 2    

    window = next(it)
    monitoring.summary.update(window)
    assert len(window.items) == 2

    window = next(it)
    monitoring.summary.update(window)
    assert len(window.items) == 1

    summary = monitoring.summary.notification
    assert monitoring.summary.has_notification == True
    
    assert summary.hits == 7
    assert summary.errors == 4
    
    assert summary.error_percentage == round((summary.errors / summary.hits) * 100, 2)
    assert summary.total_bytes == 7

    assert summary.top_k[0].name == "/api"
    assert summary.top_k[0].hits == 3

    assert summary.top_k[1].name == "/help"
    assert summary.top_k[1].hits == 2

    assert summary.top_k[2].name == "/report"
    assert summary.top_k[2].hits == 2

def test_monitoring_summary_and_alert():
    monitoring = Monitoring(
        file_path='',
        rps=2,
        summary_window_time=timedelta(seconds=1),
        alert_window_time=timedelta(seconds=1),
        ui_time_tick=0,
        hide_summary_notify=True,
        hide_alert_notify=True,
    )

    it = Log.process_log('./tests/mock.csv', waiting_time=2)
    window = next(it)
    monitoring.summary.update(window)
    monitoring.alert.update(window)
    assert len(window.items) == 3
    
    window = next(it)
    monitoring.summary.update(window)
    monitoring.alert.update(window)
    assert len(window.items) == 2    
    
    window = next(it)
    monitoring.summary.update(window)
    monitoring.alert.update(window)
    assert len(window.items) == 2

    LOGGER.info(monitoring.alert.has_notification)

    summary = monitoring.summary.notification 
    # check summary stats
    assert monitoring.summary.has_notification == True
    assert summary.hits == 5   
    assert summary.errors == 2

    # check alert stats
    assert monitoring.alert.has_notification == True
    error = monitoring.alert.errors[-1]
    assert error.rps == 5
    assert error.shown == False
    assert error.recover_at is None

    window = next(it)
    monitoring.summary.update(window)
    monitoring.alert.update(window)
    assert len(window.items) == 1

    window = next(it)
    monitoring.summary.update(window)
    monitoring.alert.update(window)
    assert len(window.items) == 1

    # recover rps
    assert monitoring.alert.has_notification == True
    error = monitoring.alert.errors[-1]
    assert error.rps == 5
    assert error.recover_at is not None
