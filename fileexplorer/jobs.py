"""User-systemd workers, durable progress, and notification acknowledgements."""
import copy
from contextlib import contextmanager
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

from . import archive, packing, credentials
from .environment import systemd_environment
from .durable import sync_directory


def atomic_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output, ensure_ascii=False)
            output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


class Jobs:
    def __init__(self, service):
        self.service = service
        self.root = service.settings_dir / 'jobs'
        self.root.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.root, 0o700)
        sync_directory(self.root.parent)
        self.lock = threading.RLock()
        self.lock_depth = 0

    @contextmanager
    def locked(self):
        """One cross-process transaction, including nested batch preparation."""
        import fcntl
        with self.lock:
            if self.lock_depth:
                self.lock_depth += 1
                try: yield
                finally: self.lock_depth -= 1
            else:
                with (self.root / 'manager.lock').open('a') as handle:
                    fcntl.flock(handle, fcntl.LOCK_EX)
                    self.lock_depth = 1
                    try: yield
                    finally: self.lock_depth = 0

    @staticmethod
    def boot_id():
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    def _folders(self):
        return [p for p in self.root.iterdir() if not p.is_symlink() and p.is_dir() and re.fullmatch('[a-f0-9]{32}', p.name)]

    def all_states(self):
        return [s for folder in self._folders() if (s := self._state(folder))]

    def list_jobs(self):
        with self.locked():
            states = self.all_states()
            boot = self.boot_id()
            for state in states:
                if state['status'] == 'queued' and state.get('boot_id') != boot:
                    state.update(status='paused', phase='Queue paused after shutdown', error='Choose Resume queue to continue.', updated=time.time())
                    atomic_json(self._folder(state['id']) / 'state.json', state)
            active = [s for s in states if s['status'] in ('running', 'queued', 'paused')]
            recent = sorted((s for s in states if s['status'] not in ('running', 'queued', 'paused') and not s.get('superseded_by')), key=lambda s: s.get('updated', 0), reverse=True)[:5]
            return sorted(active, key=lambda s: s.get('sequence', 0)) + recent

    def current_dir(self):
        try: job_id = json.loads((self.root / 'current.json').read_text())['id']
        except FileNotFoundError: return None
        return self._folder(job_id)

    def _folder(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch('[a-f0-9]{32}', job_id): raise ValueError('Invalid job identifier')
        folder = self.root / job_id
        if folder.is_symlink(): raise ValueError('Invalid job folder')
        return folder

    def state(self, job_id=None):
        folder = self._folder(job_id) if job_id else self.current_dir()
        if folder is None: return None
        return self._state(folder)

    def _state(self, folder):
        try: state = json.loads((folder / 'state.json').read_text())
        except FileNotFoundError: return None
        if state.get('id') != folder.name: raise ValueError('Invalid job state identifier')
        if state['status'] == 'running' and time.time() - state.get('updated', 0) > 12:
            check = subprocess.run(['systemctl', '--user', 'is-active', 'fileexplorer-job-' + state['id']],
                                   env=systemd_environment(), capture_output=True, text=True, timeout=5)
            if check.stdout.strip() not in ('active', 'activating'):
                state = json.loads((folder / 'state.json').read_text())
                if state['status'] != 'running': return state
                recovery = ' Saved copy progress was kept. Use Interrupted copies in Options to recover.' if state.get('recoverable') or state.get('cleanup_pending') else ' Check the destination before starting the operation again.'
                state.update(status='error', error='The background service stopped, possibly after shutdown or power loss.' + recovery, speed=0, updated=time.time())
                if state.get('cleanup_pending'): state['recoverable'] = False
                atomic_json(folder / 'state.json', state)
                (folder / 'request.json').unlink(missing_ok=True)
        return state

    def pending(self):
        result = []
        with self.locked():
            for folder in self.root.iterdir():
                if folder.is_symlink() or not folder.is_dir() or not re.fullmatch('[a-f0-9]{32}', folder.name): continue
                state = self._state(folder)
                if state and not state.get('superseded_by') and state['status'] in ('error', 'cancelled') and (state.get('recoverable') or state.get('cleanup_pending')):
                    result.append(state)
        return sorted(result, key=lambda state: state.get('updated', 0), reverse=True)

    def resolve_conflict(self, job_id, conflict_id, choice, name=None):
        if choice not in ('backup', 'overwrite', 'rename', 'cancel', 'resume'): raise ValueError('Choose Backup, Overwrite, Change name, Resume or Cancel.')
        with self.locked():
            folder = self._folder(job_id)
            state = self._state(folder)
            if not state or state['status'] != 'running': raise ValueError('This operation is no longer waiting.')
            try: conflict = json.loads((folder / 'conflict.json').read_text())
            except FileNotFoundError: raise ValueError('This conflict has already been handled.')
            if conflict.get('id') != conflict_id: raise ValueError('The conflict changed. Open the current transfer again.')
            if choice == 'resume':
                from .vfs import VFS
                profiles = self.service.profiles()
                if (folder / 'connections.json').exists(): profiles = {**json.loads((folder / 'connections.json').read_text()), **profiles}
                fs = VFS(profiles)
                try:
                    if fs.exists(conflict['target']): raise ValueError('The destination name still exists. Choose Change name or Overwrite, or remove the conflict before Resume.')
                finally: fs.close()
            if choice == 'rename':
                from .vfs import validate_name, join, parent
                name = validate_name(name)
                if join(parent(conflict['target']), name) == conflict['target']:
                    raise ValueError('Choose a different name for the incoming item.')
            response = folder / 'conflict-response.json'
            if response.exists(): raise ValueError('A choice has already been submitted.')
            atomic_json(response, dict(id=conflict_id, choice=choice, name=name))
            return True

    def restart_conflict(self, job_id, conflict_id):
        """Restart in a fresh folder only after the waiting worker has stopped."""
        self.resolve_conflict(job_id, conflict_id, 'cancel')
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            state = self.state(job_id)
            if state['status'] != 'running': break
            time.sleep(.1)
        else: raise ValueError('The transfer is still stopping. Try again from its recovery options.')
        if state['action'] == 'copy' and state.get('recoverable'): return self.retry(job_id, 'restart')
        if state['action'] not in ('move', 'copy'): raise ValueError('Restart this operation from the file list.')
        with self.locked():
            plan = json.loads((self._folder(job_id) / 'plan.json').read_text())
            sources = plan['sources'][state.get('completed', 0):]
            from .vfs import VFS, join
            fs = VFS(self.service.profiles())
            try:
                destination = join(plan['destination'], 'FileExplorer retry ' + time.strftime('%Y-%m-%d %H-%M-%S') + '-' + uuid.uuid4().hex[:6])
                fs.mkdir(destination)
            finally: fs.close()
            return self.start(state['action'], sources, destination)

    def retry(self, job_id, mode):
        if mode not in ('resume', 'restart'): raise ValueError('Choose Resume or Start again.')
        with self.locked():
            state = self.start('copy', [], retry_id=job_id, retry_mode=mode, _deferred=True)
            self.pump()
            self.ensure_dispatcher()
            return self.state(state['id'])

    def discard(self, job_id):
        with self.locked():
            state = self.start('copy', [], retry_id=job_id, retry_mode='discard', _deferred=True)
            self.pump()
            self.ensure_dispatcher()
            return self.state(state['id'])

    def forget_connection(self, key):
        with self.locked():
            for folder in self.root.iterdir():
                if folder.is_symlink() or not folder.is_dir() or not re.fullmatch('[a-f0-9]{32}', folder.name): continue
                for name in ('connections.json', 'request.json'):
                    path = folder / name
                    if not path.exists(): continue
                    value = json.loads(path.read_text())
                    profiles = value if name == 'connections.json' else value.get('connections', {})
                    if key in profiles:
                        profiles.pop(key)
                        atomic_json(path, value)

    def start_operation(self, action, sources, destination=None, options=None):
        return self.start(action, sources, destination, options=options)

    def start(self, action, sources, destination=None, retry_id=None, retry_mode=None, options=None,
              _deferred=False, _queue=None, _runtime_owner=None):
        with self.locked():
            if not _deferred and any(s['status'] in ('running', 'queued', 'paused') for s in self.all_states()):
                raise ValueError('Another operation is already running or queued')
            retry_folder = None
            profiles = self.service.profiles()
            if retry_id:
                retry_folder = self._folder(retry_id)
                old = self._state(retry_folder)
                if not old or old.get('superseded_by') or old['status'] not in ('error', 'cancelled') or not (old.get('recoverable') or retry_mode != 'resume' and old.get('cleanup_pending')):
                    raise ValueError('This operation is no longer available to resume.')
                plan = json.loads((retry_folder / 'plan.json').read_text())
                action, sources, destination = plan['action'], plan['sources'], plan['destination']
                if (retry_folder / 'connections.json').exists():
                    # Session-only logins belong to this unfinished job, not Settings.
                    profiles = {**json.loads((retry_folder / 'connections.json').read_text()), **profiles}
                if retry_mode == 'restart':
                    from .vfs import VFS, join
                    fs = VFS(profiles)
                    try:
                        destination = join(destination, 'FileExplorer retry ' + time.strftime('%Y-%m-%d %H-%M-%S') + '-' + uuid.uuid4().hex[:6])
                        fs.mkdir(destination)
                    finally: fs.close()
            sources = self.service.validate_job(action, sources, destination)
            options = packing.options(options) if action == 'pack' else None
            used = set()
            from .vfs import split
            for p in [*sources, *([destination] if destination else [])]:
                key, _ = split(archive.parse(p)[0] if archive.is_location(p) else p)
                if key: used.add(key)
            # Also protect session-only passwords before handing them to the
            # detached worker. The durable job request never contains plaintext.
            if any(key not in profiles for key in used): raise ValueError('A login for this copy was forgotten or is unavailable. Reconnect its share and start a new copy.')
            profiles = credentials.protect_profiles({key: profiles[key] for key in used})
            job_id = uuid.uuid4().hex
            folder = self.root / job_id
            folder.mkdir(mode=0o700)
            runtime = folder / 'runtime'
            source_root = Path(__file__).resolve().parents[1]
            # An immutable copy also survives a plugin update while a transfer is running.
            if not _runtime_owner:
                runtime.mkdir(mode=0o700)
                shutil.copytree(source_root / 'fileexplorer', runtime / 'fileexplorer', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                shutil.copytree(source_root / 'vendor', runtime / 'vendor', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            request = dict(action=action, sources=sources, destination=destination, options=options, home=self.service.home,
                           settings=copy.deepcopy(self.service.config['settings']), connections=profiles)
            recoverable = action == 'copy' and not any(archive.is_location(p) for p in sources)
            request['recoverable'] = recoverable
            request['discard_only'] = retry_mode == 'discard'
            atomic_json(folder / 'plan.json', dict(action=action, sources=sources, destination=destination))
            if retry_folder and retry_mode in ('resume', 'discard') and (retry_folder / 'copy.jsonl').exists():
                shutil.copyfile(retry_folder / 'copy.jsonl', folder / 'copy.jsonl')
                os.chmod(folder / 'copy.jsonl', 0o600)
                with (folder / 'copy.jsonl').open('rb') as journal: os.fsync(journal.fileno())
            if recoverable: atomic_json(folder / 'connections.json', profiles)
            atomic_json(folder / 'request.json', request)
            label = Path(split(archive.parse(sources[0])[0] if archive.is_location(sources[0]) else sources[0])[1]).name if sources else 'Trash'
            if len(sources) > 1: label += f' + {len(sources) - 1} item(s)'
            state = dict(id=job_id, action=action, kind='extract' if action == 'extract' or any(archive.is_location(p) for p in sources) else action,
                         label=label, status='running', phase='Starting background service', current='', error='', bytes=0,
                         total_bytes=0, work_bytes=0, total_work=0, speed=0, percent=0, completed=0,
                         total=len(sources) or 1, outputs=[], events=[], updated=time.time(), background=True, recoverable=recoverable)
            state.update(sequence=time.time_ns(), batch=job_id, parallel_limit=1, barrier=0,
                         boot_id=self.boot_id(), runtime_owner=_runtime_owner or job_id)
            if _queue: state.update(_queue)
            if _deferred: state.update(status='queued', phase='Waiting in queue')
            if retry_mode == 'discard': state.update(recoverable=False, cleanup_pending=True)
            atomic_json(folder / 'state.json', state)
            atomic_json(self.root / 'current.json', {'id': job_id})
            if retry_folder and retry_mode in ('resume', 'discard'):
                old['superseded_by'] = job_id
                atomic_json(retry_folder / 'state.json', old)
                (retry_folder / 'connections.json').unlink(missing_ok=True)
                sync_directory(retry_folder)
            if not _deferred: self._launch(state)
            if not _deferred: self._prune(folder)
            return state

    def _launch(self, state):
        folder = self._folder(state['id'])
        runtime = self._folder(state.get('runtime_owner', state['id'])) / 'runtime'
        state.update(status='running', phase='Starting background service', updated=time.time())
        atomic_json(folder / 'state.json', state)
        command = ['systemd-run', '--user', '--quiet', '--collect', '--service-type=exec',
                   '--unit=fileexplorer-job-' + state['id'], '--property=UMask=0077', '--property=TimeoutStopSec=20',
                   '--working-directory=' + str(runtime), '/usr/bin/python3', str(runtime / 'fileexplorer/worker.py'), str(folder)]
        try:
            result = subprocess.run(command, env=systemd_environment(), capture_output=True, text=True, timeout=15)
            if result.returncode: raise ValueError('Could not start the background service: ' + result.stderr.strip()[:300])
        except Exception:
            (folder / 'request.json').unlink(missing_ok=True)
            state.update(status='error', error='Background service could not start. No files were transferred.')
            atomic_json(folder / 'state.json', state)
            raise

    def submit_copy(self, sources, destination, mode='now', parallel_limit=1):
        if mode not in ('now', 'parallel', 'queue'): raise ValueError('Choose parallel copying or the queue.')
        if type(parallel_limit) is not int or not 1 <= parallel_limit <= 5: raise ValueError('Choose from 1 to 5 simultaneous copies.')
        with self.locked():
            sources = self.service.validate_job('copy', sources, destination)
            existing = [s for s in self.list_jobs() if s['status'] in ('running', 'queued', 'paused')]
            if mode == 'now' and existing: raise ValueError('Another transfer started. Choose Parallel or Add to queue.')
            if len(existing) + len(sources) > 10000: raise ValueError('The queue supports up to 10,000 pending items.')
            barrier = max((s.get('sequence', 0) for s in existing), default=0) if mode == 'queue' else 0
            batch = uuid.uuid4().hex
            created = []
            previous = self.current_dir()
            try:
                for source in sources:
                    state = self.start('copy', [source], destination, _deferred=True,
                        _queue=dict(batch=batch, parallel_limit=parallel_limit, barrier=barrier),
                        _runtime_owner=created[0]['id'] if created else None)
                    created.append(state)
            except Exception:
                # No worker has started while the manager transaction is held.
                for state in reversed(created): shutil.rmtree(self._folder(state['id']))
                if previous: atomic_json(self.root / 'current.json', {'id': previous.name})
                else: (self.root / 'current.json').unlink(missing_ok=True)
                raise
            self.pump()
            self.ensure_dispatcher()
            self._prune(None)
            return [self.state(s['id']) for s in created]

    def pump(self):
        """Start eligible queue entries while holding the global manager lock."""
        with self.locked():
            states = self.list_jobs()
            active = [s for s in states if s['status'] == 'running']
            for state in sorted((s for s in states if s['status'] == 'queued'), key=lambda s: s['sequence']):
                if len(active) >= 5: break
                if any(s.get('action') != 'copy' for s in active): break
                if state.get('action') != 'copy' and active: continue
                if sum(s.get('batch', s['id']) == state['batch'] for s in active) >= state['parallel_limit']: continue
                if state['barrier'] and any(s['id'] != state['id'] and s['status'] in ('running', 'queued', 'paused') and s.get('sequence', 0) <= state['barrier'] for s in states): continue
                try: self._launch(state)
                except Exception: continue  # Retain a recoverable error for this task.
                active.append(state)

    def ensure_dispatcher(self):
        queued = next((s for s in self.list_jobs() if s['status'] == 'queued'), None)
        if not queued: return
        runtime = self._folder(queued.get('runtime_owner', queued['id'])) / 'runtime'
        # Unique transient services serialize on dispatcher.lock, including the
        # narrow interval when an earlier dispatcher is about to exit.
        command = ['systemd-run', '--user', '--quiet', '--collect', '--service-type=exec',
                   '--unit=fileexplorer-queue-' + uuid.uuid4().hex, '--property=UMask=0077',
                   '--working-directory=' + str(runtime), '/usr/bin/python3', str(runtime / 'fileexplorer/dispatcher.py'),
                   str(self.service.settings_dir), str(self.service.home)]
        try:
            result = subprocess.run(command, env=systemd_environment(), capture_output=True, text=True, timeout=15)
            if not result.returncode: return
        except (OSError, subprocess.TimeoutExpired): pass
        with self.locked():
            for state in self.list_jobs():
                if state['status'] == 'queued':
                    state.update(status='paused', error='The queue service could not start. Choose Resume queue to retry.', updated=time.time())
                    atomic_json(self._folder(state['id']) / 'state.json', state)

    def resume_queue(self):
        with self.locked():
            for state in self.list_jobs():
                if state['status'] == 'paused':
                    state.update(status='queued', boot_id=self.boot_id(), error='', phase='Waiting in queue', updated=time.time())
                    atomic_json(self._folder(state['id']) / 'state.json', state)
            self.pump()
            self.ensure_dispatcher()
            return self.list_jobs()

    def _prune(self, current):
        states = self.all_states()
        if any(s['status'] in ('queued', 'paused') for s in states): return
        protected = {s.get('runtime_owner', s['id']) for s in states if not s.get('superseded_by') and (s['status'] == 'running' or s.get('recoverable') or s.get('cleanup_pending'))}
        folders = sorted((p for p in self.root.iterdir() if p.is_dir() and re.fullmatch('[a-f0-9]{32}', p.name)), key=lambda p: p.stat().st_mtime, reverse=True)
        protected.update(s.get('runtime_owner', s['id']) for s in states if self._folder(s['id']) in folders[:5])
        for folder in folders[5:]:
            if folder == current or folder.is_symlink() or folder.name in protected: continue
            try:
                state = json.loads((folder / 'state.json').read_text())
                if state['status'] != 'running' and (state.get('superseded_by') or not (state.get('recoverable') or state.get('cleanup_pending'))): shutil.rmtree(folder)
            except FileNotFoundError: pass

    def cancel(self, job_id=None, keep_partial=True):
        if type(keep_partial) is not bool: raise ValueError('Choose whether to keep partial files.')
        with self.locked():
            try: folder = self._folder(job_id) if job_id else self.current_dir()
            except ValueError: raise ValueError('This operation has already finished.')
            state = self._state(folder) if folder else None
            if not state: raise ValueError('This operation has already finished.')
            if state['status'] in ('queued', 'paused'):
                has_partial = (folder / 'copy.jsonl').exists()
                if has_partial and not keep_partial:
                    request = json.loads((folder / 'request.json').read_text())
                    request['discard_only'] = True
                    atomic_json(folder / 'request.json', request)
                    state.update(status='queued', recoverable=False, cleanup_pending=True, boot_id=self.boot_id())
                    atomic_json(folder / 'state.json', state)
                    self.ensure_dispatcher()
                else:
                    state.update(status='cancelled', recoverable=has_partial, kept_for_later=has_partial,
                                 error='Removed from queue.' + (' Partial data was kept.' if has_partial else ''), updated=time.time())
                    atomic_json(folder / 'state.json', state)
                    (folder / 'request.json').unlink(missing_ok=True)
                    if not has_partial: (folder / 'connections.json').unlink(missing_ok=True)
                return True
            if folder and state and state['status'] == 'running':
                if state.get('cleanup_pending'): raise ValueError('Wait for partial-file cleanup to finish.')
                atomic_json(folder / 'cancel', dict(keep_partial=keep_partial))
        return True

    def notifications(self, visible=False):
        result = []
        with self.locked():
            current = self.current_dir()
            for state in self.all_states():
                if state.get('superseded_by') or state.get('kind') not in ('copy', 'move', 'pack', 'extract'): continue
                folder = self._folder(state['id'])
                try: acknowledged = set(json.loads((folder / 'notified.json').read_text()))
                except FileNotFoundError: acknowledged = set()
                events = list(state.get('events', []))
                if state['status'] == 'running' and state.get('conflict'): events.append('conflict:' + state['conflict']['id'])
                if state['status'] in ('error', 'cancelled'): events.append(state['status'])
                pending = [e for e in events if e not in acknowledged]
                if pending: atomic_json(folder / 'notified.json', list(acknowledged | set(pending)))
                # Old releases only notified current.json. A multi-job upgrade
                # must not replay forgotten terminal notices from older history.
                legacy_history = 'sequence' not in state and folder != current and state['status'] != 'running'
                if not visible and not legacy_history: result.extend(dict(id=state['id'], kind=state['kind'], label=state['label'], milestone=e,
                    error=state['error'], conflict=state.get('conflict'), recoverable=state.get('recoverable', False) and not state.get('kept_for_later')) for e in pending)
        return result
