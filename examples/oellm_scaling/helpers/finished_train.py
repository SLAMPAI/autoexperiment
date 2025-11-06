#!/usr/bin/env python3
"""
finished_train.py — Return 1 if training is finished, else 0.

Usage:
    finished_train.py LOG_DIR JOB_NAME

Finds latest log starting with job_name, looks for termination string.
"""

import sys, os, re

TERMINATION_STR = 'after training is done'


def find_latest_log(log_dir, job_name):
    """Return latest <job_name>-<jobid>-<timestamp>.out inside log_dir."""
    pattern = re.compile(rf'{re.escape(job_name)}-(\d+)-([\d_-]+)\.out')
    candidates = []
    for f in os.listdir(log_dir):
        m = pattern.fullmatch(f)
        if m:
            timestamp = m.group(2)
            candidates.append((timestamp, os.path.join(log_dir, f)))
    # Pick the file with the largest timestamp (lexicographically sorted)
    return max(candidates, key=lambda x: x[0])[1] if candidates else None

def main():
    if len(sys.argv) < 3:
        print("Usage: finished_train.py LOG_DIR JOB_NAME", file=sys.stderr)
        print(0)
        return

    log_dir, job_name = sys.argv[1], sys.argv[2]
    if not os.path.isdir(log_dir):
        print(0)
        return

    logfile = find_latest_log(log_dir, job_name)
    if not logfile or not os.path.exists(logfile):
        print(0)
        return

    with open(logfile, errors="ignore") as f:
        text = f.read()

    # Job is done if termination string or KeyError found
    if re.search(rf"({TERMINATION_STR}|KeyError)", text):
        print(1)
    else:
        print(0)

if __name__ == "__main__":
    main()
