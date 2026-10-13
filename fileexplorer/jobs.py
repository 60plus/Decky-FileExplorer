"""User-systemd workers, durable progress, and notification acknowledgements."""
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path

from . import archive


def atomic_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output, ensure_ascii=False)
            output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def systemd_environment():
    # Decky's PyInstaller libraries must not replace the system tool's OpenSSL.
    env = dict(os.environ)
    original = env.pop('LD_LIBRARY_PATH_ORIG', None)
    for key in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    if original: env['LD_LIBRARY_PATH'] = original
    env.update(XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
               DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
    return env


class Jobs:
    def __init__(self, service):
        self.service = service
        self.root = service.settings_dir / 'jobs'
        self.root.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.lock = threading.RLock()

    def current_dir(self):
        try: job_id = json.loads((self.root / 'current.json').read_text())['id']
        except FileNotFoundError: return None
        if not re.fullmatch('[a-f0-9]{32}', job_id): raise ValueError('Invalid job identifier')
        return self.root / job_id

    def state(self):
        folder = self.current_dir()
        if folder is None: return None
        try: state = json.loads((folder / 'state.json').read_text())
        except FileNotFoundError: return None
        if state['status'] == 'running' and time.time() - state.get('updated', 0) > 12:
            check = subprocess.run(['systemctl', '--user', 'is-active', 'fileexplorer-job-' + state['id']],
                                   env=systemd_environment(), capture_output=True, text=True, timeout=5)
            if check.stdout.strip() not in ('active', 'activating'):
                state.update(status='error', error='The background service stopped. Completed items were kept. Check the destination before retrying.', speed=0)
                atomic_json(folder / 'state.json', state)
                (folder / 'request.json').unlink(missing_ok=True)
        return state

    def retry(self, job_id, mode):
        if mode not in ('resume', 'restart'): raise ValueError('Choose Resume or Start again.')
        return self.start('copy', [], retry_id=job_id, retry_mode=mode)

    def start(self, action, sources, destination=None, retry_id=None, retry_mode=None):
        import fcntl
        with self.lock, (self.root / 'manager.lock').open('a') as lockfile:
            fcntl.flock(lockfile, fcntl.LOCK_EX)
            current = self.state()
            if current and current['status'] == 'running': raise ValueError('Another operation is already running')
            retry_folder = None
            if retry_id:
                if not current or current['id'] != retry_id or current['status'] not in ('error', 'cancelled') or not current.get('recoverable'):
                    raise ValueError('This operation is no longer available to resume.')
                retry_folder = self.current_dir()
                plan = json.loads((retry_folder / 'plan.json').read_text())
                action, sources, destination = plan['action'], plan['sources'], plan['destination']
                if retry_mode == 'restart':
                    from .vfs import VFS, join
                    fs = VFS(self.service.profiles())
                    try:
                        destination = join(destination, 'FileExplorer retry ' + time.strftime('%Y-%m-%d %H-%M-%S') + '-' + uuid.uuid4().hex[:6])
                        fs.mkdir(destination)
                    finally: fs.close()
            sources = self.service.validate_job(action, sources, destination)
            job_id = uuid.uuid4().hex
            folder = self.root / job_id
            folder.mkdir(mode=0o700)
            runtime = folder / 'runtime'
            runtime.mkdir(mode=0o700)
            source_root = Path(__file__).resolve().parents[1]
            # An immutable copy also survives a plugin update while a transfer is running.
            shutil.copytree(source_root / 'fileexplorer', runtime / 'fileexplorer', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            shutil.copytree(source_root / 'vendor', runtime / 'vendor', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            profiles = self.service.profiles()
            used = set()
            from .vfs import split
            for p in [*sources, *([destination] if destination else [])]:
                key, _ = split(archive.parse(p)[0] if archive.is_location(p) else p)
                if key: used.add(key)
            profiles = {key: profiles[key] for key in used}
            request = dict(action=action, sources=sources, destination=destination, home=self.service.home,
                           settings=copy.deepcopy(self.service.config['settings']), connections=profiles)
            recoverable = action == 'copy' and not any(archive.is_location(p) for p in sources)
            request['recoverable'] = recoverable
            atomic_json(folder / 'plan.json', dict(action=action, sources=sources, destination=destination))
            if retry_folder and retry_mode == 'resume' and (retry_folder / 'copy.jsonl').exists():
                shutil.copyfile(retry_folder / 'copy.jsonl', folder / 'copy.jsonl')
                os.chmod(folder / 'copy.jsonl', 0o600)
            atomic_json(folder / 'request.json', request)
            label = Path(split(archive.parse(sources[0])[0] if archive.is_location(sources[0]) else sources[0])[1]).name if sources else 'Trash'
            if len(sources) > 1: label += f' + {len(sources) - 1} item(s)'
            state = dict(id=job_id, action=action, kind='extract' if action == 'extract' or any(archive.is_location(p) for p in sources) else action,
                         label=label, status='running', phase='Starting background service', current='', error='', bytes=0,
                         total_bytes=0, work_bytes=0, total_work=0, speed=0, percent=0, completed=0,
                         total=len(sources) or 1, outputs=[], events=[], updated=time.time(), background=True, recoverable=recoverable)
            atomic_json(folder / 'state.json', state)
            atomic_json(self.root / 'current.json', {'id': job_id})
            command = ['systemd-run', '--user', '--quiet', '--collect', '--service-type=exec',
                       '--unit=fileexplorer-job-' + job_id, '--property=UMask=0077', '--property=TimeoutStopSec=20',
                       '--working-directory=' + str(runtime), '/usr/bin/python3', str(runtime / 'fileexplorer/worker.py'), str(folder)]
            try:
                result = subprocess.run(command, env=systemd_environment(), capture_output=True, text=True, timeout=15)
                if result.returncode: raise ValueError('Could not start the background service: ' + result.stderr.strip()[:300])
            except Exception:
                (folder / 'request.json').unlink(missing_ok=True)
                state.update(status='error', error='Background service could not start. No files were transferred.')
                atomic_json(folder / 'state.json', state)
                raise
            self._prune(folder)
            return state

    def _prune(self, current):
        folders = sorted((p for p in self.root.iterdir() if p.is_dir() and re.fullmatch('[a-f0-9]{32}', p.name)), key=lambda p: p.stat().st_mtime, reverse=True)
        for folder in folders[5:]:
            if folder == current or folder.is_symlink(): continue
            try:
                state = json.loads((folder / 'state.json').read_text())
                if state['status'] != 'running': shutil.rmtree(folder)
            except FileNotFoundError: pass

    def cancel(self, job_id=None):
        folder = self.current_dir()
        state = self.state()
        if job_id and state and state['id'] != job_id: raise ValueError('This operation has already finished.')
        if folder and state and state['status'] == 'running': (folder / 'cancel').touch(mode=0o600)
        return True

    def notifications(self, visible=False):
        with self.lock:
            state = self.state()
            if not state or state['kind'] not in ('copy', 'extract'): return []
            folder = self.current_dir()
            try: acknowledged = set(json.loads((folder / 'notified.json').read_text()))
            except FileNotFoundError: acknowledged = set()
            events = list(state.get('events', []))
            if state['status'] in ('error', 'cancelled'): events.append(state['status'])
            pending = [e for e in events if e not in acknowledged]
            if pending: atomic_json(folder / 'notified.json', list(acknowledged | set(pending)))
            return [] if visible else [dict(id=state['id'], kind=state['kind'], label=state['label'], milestone=e,
                                           error=state['error'], recoverable=state.get('recoverable', False)) for e in pending]
