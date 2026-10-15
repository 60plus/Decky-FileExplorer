"""Detached queue dispatcher. Workers stay separate; at most five copies run."""
import fcntl
from pathlib import Path
import sys
import time

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'vendor'), str(root)]
from fileexplorer.jobs import Jobs
from fileexplorer.service import Service


def run(settings, home):
    service = Service(home, settings)
    jobs = Jobs(service)
    try:
        with (jobs.root / 'dispatcher.lock').open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            while True:
                jobs.pump()
                if not any(s['status'] == 'queued' for s in jobs.list_jobs()): break
                time.sleep(.5)
    finally:
        service.shutdown()


if __name__ == '__main__': run(sys.argv[1], sys.argv[2])
