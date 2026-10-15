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


def discard_partial(folder, service, request, state):
    from fileexplorer.vfs import VFS
    state.update(status='running', phase='Removing partial copies', speed=0, recoverable=False,
                 cleanup_pending=True, updated=time.time())
    atomic_json(folder / 'state.json', state)
    fs = VFS(service.profiles())
    try:
        service.copy_resume.discard(fs, request['sources'], request['destination'])
        state.update(status='cancelled', cleanup_pending=False, partial_removed=True,
                     error='Copy stopped. Unfinished copies were removed; completed destination items were kept.')
    except Exception as error:
        state.update(status='error', error='Partial-file cleanup could not finish. Remaining data was kept. '
                     'Retry removal from Options > Interrupted copies. ' + error_message(error))
    finally:
        fs.close()
        state['updated'] = time.time()
        atomic_json(folder / 'state.json', state)


def run(folder):
    folder = Path(folder)
    previous = json.loads((folder / 'state.json').read_text())
    service = None
    try:
        request = json.loads((folder / 'request.json').read_text())
        (folder / 'request.json').unlink()  # Encrypted credentials are now held by the worker.
        service = Service(request['home'], folder / 'engine')
        service.config['settings'].update(request['settings'])
        service.session_connections = request['connections']
        from fileexplorer.conflicts import Interaction, Replacement
        interaction = Interaction(folder, service)
        service.replacement = Replacement(folder, interaction.ask, service.progress)
        if request.get('recoverable'):
            from fileexplorer.copy_resume import CopyResume
            service.copy_resume = CopyResume(folder / 'copy.jsonl', service.progress, interaction.ask)
        signal.signal(signal.SIGTERM, lambda *_: service.cancel.set())
        signal.signal(signal.SIGINT, lambda *_: service.cancel.set())
        if request.get('discard_only'):
            discard_partial(folder, service, request, previous)
            if not previous.get('cleanup_pending'): (folder / 'connections.json').unlink(missing_ok=True)
            return
        service.start(request['action'], request['sources'], request['destination'], options=request.get('options'))
        events = []
        while True:
            cancel_path = folder / 'cancel'
            if cancel_path.exists(): service.cancel.set()
            state = service.job_state()
            for threshold in (25, 50, 75, 100):
                if state['percent'] >= threshold and threshold not in events: events.append(threshold)
            state.update(id=previous['id'], kind=previous['kind'], label=previous['label'],
                         recoverable=request.get('recoverable', False),
                         events=events, updated=time.time(), background=True)
            state.update({key: previous[key] for key in ('sequence', 'batch', 'parallel_limit', 'barrier', 'boot_id', 'runtime_owner') if key in previous})
            if state['status'] != 'running':
                if state['status'] != 'done' and state['recoverable'] and cancel_path.exists():
                    try: keep = json.loads(cancel_path.read_text()).get('keep_partial', True)
                    except (ValueError, OSError): keep = True  # Old markers mean preserve data.
                    if not keep:
                        discard_partial(folder, service, request, state)
                    elif state['status'] == 'cancelled':
                        state['kept_for_later'] = True
                        state['error'] = 'Copy stopped. Partial data was kept. Resume later from Options > Interrupted copies.'
                if state['status'] == 'done': state['recoverable'] = False
                if not state.get('recoverable') and not state.get('cleanup_pending'):
                    (folder / 'connections.json').unlink(missing_ok=True)
                atomic_json(folder / 'state.json', state)
                break
            atomic_json(folder / 'state.json', state)
            time.sleep(.2)
    except Exception as error:
        previous.update(status='error', error=error_message(error), speed=0, updated=time.time())
        atomic_json(folder / 'state.json', previous)
    finally:
        (folder / 'request.json').unlink(missing_ok=True)
        if service: service.shutdown()


if __name__ == '__main__': run(sys.argv[1])
