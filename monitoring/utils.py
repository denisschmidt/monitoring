"""Test file generator.
This script emulates writing to a log file in real time. It will help you to test the monitoring console program

Usage:
  utils.py [options]

Options:
  --file_path=<str>    The file to write to. [default: ./logs/test.csv].
  --rounds=<int>       Number of rounds [default: 100].
  --batch_size=<int>   The number of lines in one batch when writing to a file [default: 100].
  --rps=<int>          Approximate rps value. Normal distribution with mean=rps [default: 10].
"""

import csv
import os
import random

from docopt import docopt
from time import sleep


def generate_test_data(start_time=1549574332, n_rows=1000, rps=100):
    data = [["remotehost", "rfc931", "authuser", "date", "request", "status", "bytes"]]

    i = 0
    while i < n_rows:
        start_time += 1
        per_sec = max(0, int(random.gauss(rps, int(rps * 0.25))))
        j = 0
        while i < n_rows and j < per_sec:
            j += 1
            i += 1
            host = random.choice(["10.0.0.1", "10.0.0.4", "127.0.0.1"])
            req_type = random.choice(["GET", "POST", "PUT", "DELETE"])
            section = random.choice(["/api/user", "/report", "/test", "/help/me"])
            size = random.randint(1000, 4000)
            status = random.randint(200, 599)
            data.append([host, "-", "apache", start_time, f"{req_type} {section} HTTP/1.0", status, size])

    return data


def start_load_test(file_path: str, rounds: int, batch_size: int, rps: int):
    data = generate_test_data(n_rows=rounds * batch_size, rps=rps)
    try:
        os.remove(file_path)
    except OSError:
        pass

    for r in range(rounds):
        print(f"Round: {r}")
        with open(file_path, 'a+', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data[r * batch_size:(r + 1) * batch_size])
        sleep(random.randint(1, 30))


if __name__ == "__main__":
    args = docopt(__doc__, version='Test file generator')
    start_load_test(args["--file_path"], int(args["--rounds"]), int(args["--batch_size"]), int(args["--rps"]))
