"""Entry point for one transient systemd user service. No Decky imports."""
import json
import signal
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'vendor'), str(root)]
from fileexplorer.jobs import atomic_json
from fileexplorer.service import Service, error_message


def run(folder):
    folder = Path(folder)
    previous = json.loads((folder / 'state.json').read_text())
    service = None
    try:
        request = json.loads((folder / 'request.json').read_text())
        (folder / 'request.json').unlink()  # Credentials remain only in worker memory.
        service = Service(request['home'], folder / 'engine')
        service.config['settings'].update(request['settings'])
        service.session_connections = request['connections']
        if request.get('recoverable'):
            from fileexplorer.copy_resume import CopyResume
            service.copy_resume = CopyResume(folder / 'copy.jsonl', service.progress)
        signal.signal(signal.SIGTERM, lambda *_: service.cancel.set())
        signal.signal(signal.SIGINT, lambda *_: service.cancel.set())
        service.start(request['action'], request['sources'], request['destination'])
        events = []
        while True:
            if (folder / 'cancel').exists(): service.cancel.set()
            state = service.job_state()
            for threshold in (25, 50, 75, 100):
                if state['percent'] >= threshold and threshold not in events: events.append(threshold)
            state.update(id=previous['id'], kind=previous['kind'], label=previous['label'],
                         recoverable=request.get('recoverable', False),
                         events=events, updated=time.time(), background=True)
            atomic_json(folder / 'state.json', state)
            if state['status'] != 'running': break
            time.sleep(.2)
    except Exception as error:
        previous.update(status='error', error=error_message(error), speed=0, updated=time.time())
        atomic_json(folder / 'state.json', previous)
    finally:
        (folder / 'request.json').unlink(missing_ok=True)
        if service: service.shutdown()


if __name__ == '__main__': run(sys.argv[1])
