"""Monitoring Tool. 

This is a command line interface(CLI) that helps you to analyze log metrics.

Usage:
  monitoring-tool.py [options]

Options:
  --file_path=<str>            Folder where the configuration file is stored. [default: ./logs/test.csv].
  --summary_window_time=<int>  Summary notification time in sec [default: 10].
  --rps=<int>                  Set up RPS [default: 10].
  --alert_window_time=<float>  Alert notification time in sec [default: 30].
  --ui_time_tick=<float>       Console terminal update frequency [default: 2].
  --hide_summary_notify        Show notify for every N seconds of log lines, display stats about the traffic during those N sec [default: false].
  --hide_alert_notify          Show notify if total traffic for the past N minutes exceeds a certain number on average [default: false].
  -X --debug                   Enable debugging logs. [default: false].
"""

from pathlib import Path
from datetime import timedelta
from docopt import docopt
import logging
from monitoring.monitoring import Monitoring

def main():
    args = docopt(__doc__, version='Monitoring Tool 2.0') 
    debug = args["--debug"]
    file_path = args["--file_path"]
    summary_window_time = int(args["--summary_window_time"])
    alert_window_time = int(args["--alert_window_time"])
    ui_time_tick = float(args["--ui_time_tick"])
    hide_summary_notify = args["--hide_summary_notify"]
    hide_alert_notify = args["--hide_alert_notify"]
    rps = int(args["--rps"])

    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    home = Path.home()
    logging.debug(f"args={args}")
    logging.debug(f"home={home}")

    if "--file_path" in args:
        logging.debug(f"User provided argument '--file_path'")
        logging.debug(f"file_path={file_path}")
    else:
        raise Exception('Please provide --file_path')
    
    monitoring = Monitoring(
        file_path=file_path,
        rps=rps,
        summary_window_time=timedelta(seconds=summary_window_time), 
        alert_window_time=timedelta(seconds=alert_window_time),
        ui_time_tick=ui_time_tick,
        hide_summary_notify=hide_summary_notify,
        hide_alert_notify=hide_alert_notify,
    )
    monitoring.run()

if __name__ == "__main__":
    main()
