import copy
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import posixpath
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from . import archive, discovery, trash, editor, images, moving, packing, credentials
from .media import Media
from .updates import installed_version
from .vfs import VFS, join, parent, split, validate_name
from .drafts import Drafts

DEFAULTS = dict(show_hidden=False, folders_first=True, sort_by='name', remember_paths=True,
                left='', right='', extraction_limit_gib=100, accent='cyan', opacity=100, text_size=14, ui_scale=100, legend_mode='both', check_updates_on_start=True,
                toolbar_hidden=False, setup_completed=False, profile='', splash_enabled=False, splash_seen=False)
# First-time setup presets. Only the chosen profile plus Save writes them;
# existing personalisation stays untouched until then.
_SETUP_SHARED = dict(opacity=100, text_size=14, show_hidden=True, folders_first=True, remember_paths=True,
                     check_updates_on_start=True, sort_by='name', splash_enabled=False)
PROFILES = dict(handheld=dict(_SETUP_SHARED, ui_scale=70, legend_mode='panel', toolbar_hidden=True),
                pc=dict(_SETUP_SHARED, ui_scale=100, legend_mode='steam', toolbar_hidden=False))


class Cancelled(Exception):
    pass


class Service:
    def __init__(self, home, settings):
        self.home = str(Path(home).resolve())
        self.settings_dir = Path(settings)
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.settings_dir, 0o700)
        self.config_file = self.settings_dir / 'settings.json'
        self.lock = threading.RLock()
        self.config = dict(settings=DEFAULTS.copy(), connections={})
        if self.config_file.exists():
            saved = json.loads(self.config_file.read_text())
            self.config['settings'].update(saved.get('settings', {}))
            self.config['connections'] = saved.get('connections', {})
        self.session_connections = {}
        self.session_warnings = {}
        self.drafts = Drafts(self.settings_dir)
        self.job = None
        self.cancel = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='fileexplorer')
        self.archive_cache = {}
        self.archive_lock = threading.Lock()
        self._speed_samples = []
        self._archive_work_files = None
        self.media = Media()
        self.copy_resume = None
        self.replacement = None
        self.credential_error = ''
        if any('password' in p for p in self.config['connections'].values()):
            try: self.save()
            except (credentials.CredentialError, OSError):
                self.credential_error = ('Saved SMB passwords could not be migrated to encrypted storage. '
                                         'Existing connections are kept, but their old settings file is still unencrypted. '
                                         'Check systemd credential support and reload FileExplorer to retry.')

    def profiles(self):
        with self.lock:
            return copy.deepcopy({**self.config['connections'], **self.session_connections})

    def save(self):
        # Encrypt and verify before replacing any existing plaintext config.
        candidate = copy.deepcopy(self.config)
        candidate['connections'] = credentials.protect_profiles(candidate['connections'])
        fd, tmp = tempfile.mkstemp(dir=self.settings_dir, prefix='.settings-')
        try:
            os.fchmod(fd, 0o600) if hasattr(os, 'fchmod') else None
            with os.fdopen(fd, 'w') as f:
                json.dump(candidate, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.config_file)
            self.config = candidate
            self.credential_error = ''
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

    def state(self):
        with self.lock:
            settings = copy.deepcopy(self.config['settings'])
        if not settings['remember_paths']:
            settings['left'] = settings['right'] = self.home
        settings['left'] = settings['left'] or self.home
        settings['right'] = settings['right'] or self.home
        connections = [{k: v for k, v in p.items() if k in ('host', 'share', 'username', 'domain', 'label', 'port')} |
                       {'id': key, 'saved': key in self.config['connections'],
                        'password_storage': credentials.storage_for(p, key in self.config['connections'])}
                       for key, p in self.profiles().items()]
        warnings = [self.credential_error, *self.session_warnings.values()]
        return dict(settings=settings, connections=connections, credential_error=' '.join(filter(None, warnings)),
                    home=self.home, version=installed_version(), job=self.job_state())

    @staticmethod
    def validate_settings(changes):
        # Check every value before anything is applied, so one invalid key
        # cannot leave a partially updated configuration behind.
        allowed = {'show_hidden', 'folders_first', 'remember_paths', 'check_updates_on_start', 'toolbar_hidden', 'setup_completed', 'splash_enabled'}
        valid = {}
        for key, value in changes.items():
            if key in allowed and type(value) is bool: valid[key] = value
            elif key == 'sort_by' and value in ('name', 'size', 'modified'): valid[key] = value
            elif key == 'accent' and value in ('cyan', 'blue', 'green', 'amber', 'violet', 'rose'): valid[key] = value
            elif key == 'opacity' and type(value) is int and value in (70, 85, 100): valid[key] = value
            elif key == 'text_size' and type(value) is int and value in (12, 14, 16, 18): valid[key] = value
            elif key == 'ui_scale' and type(value) is int and value in (70, 80, 90, 100): valid[key] = value
            elif key == 'legend_mode' and value in ('panel', 'steam', 'both', 'none'): valid[key] = value
            elif key == 'profile' and value in ('handheld', 'pc', ''): valid[key] = value
            elif key in ('left', 'right') and isinstance(value, str):
                archive.parse(value) if archive.is_location(value) else split(value)
                valid[key] = value
            elif key == 'extraction_limit_gib' and type(value) is int and 0 <= value <= 1000: valid[key] = value
            else: raise ValueError('Invalid setting: ' + str(key))
        return valid

    def _commit_settings(self, valid):
        # Settings change as one transaction: a failed save leaves memory as it was.
        with self.lock:
            previous = self.config['settings']
            self.config['settings'] = {**previous, **valid}
            try: self.save()
            except BaseException:
                self.config['settings'] = previous
                raise
        return self.state()

    def update_settings(self, changes):
        return self._commit_settings(self.validate_settings(changes))

    def setup_profiles(self):
        return copy.deepcopy(PROFILES)

    def claim_splash(self):
        # Independent of setup completion: cancelling the wizard must not replay
        # the first-launch image. Serialize competing launches before saving.
        with self.lock:
            settings = self.config['settings']
            first = not settings['splash_seen']
            show = first or settings['splash_enabled']
            if first: self._commit_settings({'splash_seen': True})
            return dict(show=show)

    def setup(self, profile, changes=None):
        # Apply a first-setup profile with the user's edits from the last step.
        if profile not in PROFILES: raise ValueError('Unknown profile: ' + str(profile))
        changes = dict(changes or {})
        for key in ('profile', 'setup_completed', 'splash_seen'):
            if key in changes: raise ValueError('Invalid setting: ' + key)
        valid = self.validate_settings({**PROFILES[profile], **changes})
        return self._commit_settings({**valid, 'profile': profile, 'setup_completed': True})

    def list_dir(self, location):
        fs = VFS(self.profiles())
        try:
            virtual = archive.is_location(location)
            label = None
            if virtual:
                source, member = archive.parse(location)
                manifest = self._archive_manifest(fs, source)
                if member and (member not in manifest or not manifest[member]['directory']):
                    raise ValueError('Archive folder not found')
                entries = [dict(name=posixpath.basename(name), path=archive.location(source, name),
                                link=False, hidden=posixpath.basename(name).startswith('.'), **info)
                           for name, info in manifest.items() if posixpath.dirname(name) == member]
                if split(source)[0]:
                    key, path = split(source)
                    profile = fs.profiles[key]
                    label = 'smb://' + profile['host'] + '/' + profile['share'] + path
                else: label = source
                label += ' / ' + member
            else: entries = fs.listing(location)
            with self.lock: settings = self.config['settings'].copy()
            if not settings['show_hidden']: entries = [e for e in entries if not e['hidden']]
            field = settings['sort_by']
            entries.sort(key=lambda e: e['name'].casefold())
            if field != 'name': entries.sort(key=lambda e: e[field], reverse=True)
            if settings['folders_first']: entries.sort(key=lambda e: not e['directory'])
            free = None
            if not virtual and not split(location)[0]: free = shutil.disk_usage(location).free
            return dict(path=location, parent=archive.parent(location) if virtual else parent(location),
                        entries=entries, free=free, archive=virtual, label=label)
        finally: fs.close()

    def open_archive(self, location):
        if archive.is_location(location):
            raise ValueError('Copy this nested archive to a folder first, then open it.')
        return dict(path=archive.location(location))

    def extraction_limit(self):
        gib = self.config['settings']['extraction_limit_gib']
        return gib * 1024**3 if gib else None

    @contextmanager
    def _archive_file(self, fs, source, progress=lambda *_: None):
        limit = self.extraction_limit()
        info = fs.info(source)
        if info['directory'] or info['link'] or not info.get('regular', True):
            raise ValueError('Open a regular archive file')
        if not split(source)[0]:
            yield source
            return
        if self._archive_work_files is not None and source in self._archive_work_files:
            yield self._archive_work_files[source]
            return
        if self._archive_work_files is not None:
            local = Path(self._archive_scratch) / uuid.uuid4().hex
            received = 0
            def bounded(n, name):
                nonlocal received
                received += n
                if limit is not None and received > limit: raise archive.size_limit_error(limit, remote=True)
                self.staging_progress(n, name)
            with local.open('xb') as out: fs.read_to(source, out, bounded)
            self._archive_work_files[source] = local
            yield local
            return
        with tempfile.TemporaryDirectory(prefix='.fileexplorer-read-', dir=self.settings_dir) as scratch:
            local = Path(scratch) / 'archive'
            received = 0
            def bounded(n, name):
                nonlocal received
                received += n
                if limit is not None and received > limit:
                    raise archive.size_limit_error(limit, remote=True)
                progress(n, name)
            with local.open('xb') as out: fs.read_to(source, out, bounded)
            yield local

    def _archive_manifest(self, fs, source):
        info = fs.info(source)
        stamp = (info['size'], info['modified'], self.extraction_limit())
        with self.archive_lock:
            cached = self.archive_cache.get(source)
            if cached and cached[0] == stamp: return cached[1]
            with self._archive_file(fs, source) as local:
                entries = archive.manifest(local, self.extraction_limit(), self.staging_progress if self._archive_work_files is not None else lambda *_: None)
            if len(self.archive_cache) >= 8: self.archive_cache.pop(next(iter(self.archive_cache)))
            self.archive_cache[source] = (stamp, entries)
            return entries

    def locations(self):
        locations = [dict(name='Home', path=self.home), dict(name='Filesystem', path='/')]
        for label, p in [('Downloads', Path(self.home) / 'Downloads'), ('Removable drives', Path('/run/media'))]:
            if p.is_dir(): locations.append(dict(name=label, path=str(p)))
        for root in (Path('/run/media') / Path(self.home).name, Path('/run/media'), Path('/mnt'), Path('/media'),
                     Path('/run/user') / str(os.getuid()) / 'gvfs' if hasattr(os, 'getuid') else Path(self.home) / '.gvfs'):
            if root.is_dir():
                try:
                    for p in root.iterdir():
                        if p.is_dir() and (os.path.ismount(p) or root.name == 'gvfs'):
                            locations.append(dict(name=p.name, path=str(p)))
                except PermissionError: pass
        for key, p in self.profiles().items():
            locations.append(dict(name=p['label'], path='smb://' + key + '/', connection=key))
        return list({x['path']: x for x in locations}.values())

    def _clean_profile(self, profile, require_share=True):
        clean = {}
        for k in ('host', 'share', 'username', 'password', 'domain', 'label'):
            v = profile.get(k, '')
            if not isinstance(v, str) or len(v) > 1024 or '\x00' in v: raise ValueError('Invalid connection field')
            clean[k] = v.strip() if k != 'password' else v
        if not clean['host'] or any(c in clean['host'] for c in '/\\@: '):
            raise ValueError('Enter a server name or IPv4 address, without smb://')
        if require_share: validate_name(clean['share'])
        port = profile.get('port', 445)
        if type(port) is not int or not 1 <= port <= 65535: raise ValueError('Invalid SMB port')
        clean['port'] = port
        clean['label'] = clean['label'] or clean['host'] + ' / ' + clean['share']
        return clean

    def discover(self):
        return discovery.discover()

    def shares(self, profile):
        clean = self._clean_profile(profile, require_share=False)
        # Reuse a saved login only when the UI explicitly selects that connection.
        saved = profile.get('connection_id')
        if saved:
            known = self.profiles().get(saved)
            if not known or known['host'] != clean['host']: raise ValueError('Saved connection not found')
            clean = known
        key = saved or 'discovery'
        fs = VFS({key: clean})
        try:
            conn, _ = fs.remote(key)
            return [dict(name=s.name, comment=s.comments or '') for s in conn.listShares(timeout=15)
                    if s.type & 0xffff == 0]
        finally: fs.close()

    def connect(self, profile):
        clean = self._clean_profile(profile)
        key = uuid.uuid4().hex
        fs = VFS({key: clean})
        try: fs.listing('smb://' + key + '/')
        finally: fs.close()
        with self.lock:
            if profile.get('remember') is True:
                self.config['connections'][key] = clean
                try: self.save()
                except credentials.CredentialError:
                    self.config['connections'].pop(key, None)
                    self.session_connections[key] = clean
                    self.session_warnings[key] = ('Secure password storage is unavailable. The new SMB connection is '
                                                  'available for this session only; its password was not saved.')
                except Exception:
                    self.config['connections'].pop(key, None)
                    raise
            else: self.session_connections[key] = clean
        return dict(path='smb://' + key + '/', id=key)

    def forget(self, key):
        with self.lock:
            self.config['connections'].pop(key, None)
            self.session_connections.pop(key, None)
            self.session_warnings.pop(key, None)
            self.save()
        return True

    def _protect(self, path):
        key, p = split(path)
        if key:
            if p == '/': raise ValueError('Cannot modify the share root')
        elif os.path.realpath(p) in ('/', self.home) or os.path.ismount(p):
            raise ValueError('Cannot modify a home directory, filesystem or mount root')

    def mkdir(self, location, name):
        with self.lock:
            if self.job and self.job['status'] == 'running': raise ValueError('Wait for the current operation')
        fs = VFS(self.profiles())
        try:
            target = join(location, name)
            fs.mkdir(target)
            return target
        finally: fs.close()

    def rename(self, location, name):
        with self.lock:
            if self.job and self.job['status'] == 'running': raise ValueError('Wait for the current operation')
        self._protect(location)
        fs = VFS(self.profiles())
        try:
            target = join(parent(location), name)
            fs.rename(location, target)
            return target
        finally: fs.close()

    def preview(self, location):
        if archive.is_location(location):
            return dict(text=None, size=0, message='Select this item with X, then use Copy / Extract to unpack it into the other panel.')
        fs = VFS(self.profiles())
        try:
            info = fs.info(location)
            if info['directory'] or info['link'] or not info.get('regular', True) or info['size'] > 256 * 1024:
                return dict(text=None, size=info['size'], message='Text preview supports regular files up to 256 KiB.')
            import io
            output = io.BytesIO()
            def bounded(n, _):
                if output.tell() + n > 256 * 1024: raise ValueError('Preview is too large')
            fs.read_to(location, output, bounded)
            raw = output.getvalue()
            if b'\0' in raw: return dict(text=None, size=info['size'], message='Binary file. Use Options to copy, rename or extract.')
            return dict(text=raw.decode('utf-8', errors='replace'), size=info['size'], message='')
        finally: fs.close()

    def image(self, location):
        fs = VFS(self.profiles())
        try:
            if not archive.is_location(location): return images.read(fs, location)
            source, member = archive.parse(location)
            if not member: raise ValueError('Choose an image inside the archive.')
            with self._archive_file(fs, source) as local:
                entries = archive.manifest(local)
                info = entries.get(member)
                if not info or info['directory']: raise ValueError('Image not found in archive.')
                if info['size'] > images.LIMIT: raise ValueError('Image preview supports files up to 20 MiB.')
                with tempfile.TemporaryDirectory(prefix='.fileexplorer-image-', dir=self.settings_dir) as scratch:
                    archive.extract(local, scratch, lambda *_: None, limit=images.LIMIT, selected=[member])
                    return images.read(fs, str(Path(scratch) / member))
        finally: fs.close()

    def read_text(self, location, encoding=None):
        fs = VFS(self.profiles())
        try: return editor.read(fs, location, encoding)
        finally: fs.close()

    def open_media(self, location):
        return self.media.open(location, self.profiles())

    def close_media(self, token):
        return self.media.close(token)

    def save_text(self, location, text, revision, encoding=None):
        fs = VFS(self.profiles())
        try: return editor.save(fs, location, text, revision, encoding)
        finally: fs.close()

    def job_state(self):
        with self.lock:
            if self.job is None: return None
            result = copy.deepcopy(self.job)
            samples = self._speed_samples
            now = time.monotonic()
            result['speed'] = ((samples[-1][1] - samples[0][1]) / max(.1, samples[-1][0] - samples[0][0])) if len(samples) > 1 and now - samples[-1][0] < 2 else 0
            if result['status'] != 'running': result['speed'] = 0
            total = result.get('total_work', 0)
            result['percent'] = 100 if result['status'] == 'done' else min(99, int(100 * result.get('work_bytes', 0) / total)) if total else 0
            return result

    def progress(self, n, name):
        self._progress(n, name, True)

    def staging_progress(self, n, name):
        self._progress(n, name, False)

    def _progress(self, n, name, output):
        if self.cancel.is_set(): raise Cancelled('Cancelled. Completed items have been kept.')
        with self.lock:
            if output: self.job['bytes'] += n
            self.job['work_bytes'] = self.job.get('work_bytes', 0) + n
            self.job['current'] = name
            phases = {'copy': 'Copying', 'move': 'Moving / verifying', 'pack': 'Packing',
                      'trash': 'Moving to Trash', 'delete': 'Deleting', 'empty_trash': 'Emptying Trash'}
            self.job['phase'] = phases.get(self.job['action'], 'Extracting') if output else 'Preparing'
            now = time.monotonic()
            if n and (not self._speed_samples or now - self._speed_samples[-1][0] >= .1):
                self._speed_samples.append((now, self.job['work_bytes']))
                while len(self._speed_samples) > 2 and now - self._speed_samples[0][0] > 3: self._speed_samples.pop(0)

    def validate_job(self, action, sources, destination=None):
        if action not in ('copy', 'move', 'pack', 'extract', 'trash', 'delete', 'empty_trash'): raise ValueError('Unknown operation')
        if not isinstance(sources, list) or (not sources and action != 'empty_trash') or len(sources) > 10000: raise ValueError('Select files first')
        if action == 'empty_trash' and sources: raise ValueError('Empty Trash does not accept paths')
        sources = list(dict.fromkeys(sources))
        for p in sources:
            if archive.is_location(p):
                _, member = archive.parse(p)
                if action != 'copy' or not member: raise ValueError('Archive contents are read-only. Copy selected items to extract them.')
            else:
                split(p)
                self._protect(p)
        if action in ('copy', 'move', 'pack', 'extract'):
            if archive.is_location(destination): raise ValueError('Choose a writable folder in the other panel. Archives are read-only.')
            split(destination)
        if action in ('move', 'pack'):
            fs = VFS(self.profiles())
            try:
                groups = {}
                for p in sources:
                    if moving.inside(fs, destination, p): raise ValueError('Choose a destination outside the selected folder')
                    key, path = moving.identity(fs, p)
                    groups.setdefault(key, []).append(path)
                for paths in groups.values():
                    seen = set()
                    for path in paths:
                        if path in seen: raise ValueError('Select each item only once')
                        seen.add(path)
                    for path in paths:
                        ancestor = posixpath.dirname(path)
                        while ancestor != posixpath.dirname(ancestor):
                            if ancestor in seen: raise ValueError('Select the parent folder once, without also selecting its contents')
                            ancestor = posixpath.dirname(ancestor)
            finally: fs.close()
        if action == 'trash' and any(split(p)[0] for p in sources): raise ValueError('SMB files require permanent deletion')
        if action == 'delete' and any(not split(p)[0] for p in sources): raise ValueError('Local files must use Trash')
        return sources

    def start(self, action, sources, destination=None, options=None):
        sources = self.validate_job(action, sources, destination)
        options = packing.options(options) if action == 'pack' else None
        with self.lock:
            if self.job and self.job['status'] == 'running': raise ValueError('Another operation is already running')
            self.cancel.clear()
            self.job = dict(id=uuid.uuid4().hex, action=action, status='running', bytes=0, current='',
                            completed=0, total=len(sources) if action != 'empty_trash' else 1, error='', outputs=[],
                            total_bytes=0, work_bytes=0, total_work=0, phase='Preparing', speed=0, percent=0,
                            label=Path(split(archive.parse(sources[0])[0] if archive.is_location(sources[0]) else sources[0])[1]).name if sources else 'Trash')
            self._speed_samples = [(time.monotonic(), 0)]
            self.executor.submit(self._work, action, sources, destination, options)
            return self.job.copy()

    def _estimate_tree(self, fs, source, depth=0):
        if depth > 128: raise ValueError('Folder nesting is too deep')
        self.staging_progress(0, source)
        info = fs.info(source)
        if info['link'] or not info.get('regular', True) and not info['directory']:
            raise ValueError('Copying links and special files is not supported')
        if info['directory']: return sum(self._estimate_tree(fs, e['path'], depth + 1) for e in fs.listing(source))
        return info['size']

    def _plan(self, fs, action, sources, destination):
        total = work = 0
        if action == 'pack':
            self._packing_entries = packing.plan(fs, sources, destination, self.staging_progress)
            total = sum(info['size'] for _, _, info in self._packing_entries if not info['directory'])
            work = total * (2 if split(destination)[0] else 1)
        elif action in ('copy', 'move', 'extract'):
            virtual = [p for p in sources if archive.is_location(p)]
            for source in dict.fromkeys(archive.parse(p)[0] for p in virtual):
                members = [archive.parse(p)[1] for p in virtual if archive.parse(p)[0] == source]
                manifest = self._archive_manifest(fs, source)
                size = sum(e['size'] for name, e in manifest.items() if not e['directory'] and any(name == s or name.startswith(s + '/') for s in members))
                total += size; work += size * 2
            for source in sources:
                if archive.is_location(source): continue
                if action == 'extract':
                    size = sum(e['size'] for e in self._archive_manifest(fs, source).values() if not e['directory'])
                    total += size; work += size
                else:
                    size = self._estimate_tree(fs, source)
                    staged_remote = self.copy_resume is None and split(source)[0] and split(destination)[0]
                    total += size; work += size * (3 if action == 'move' else 2 if staged_remote else 1)
        with self.lock:
            self.job.update(total_bytes=total, total_work=work, work_bytes=0, bytes=0, phase='Starting')
            self._speed_samples = [(time.monotonic(), 0)]

    def _copy_tree(self, fs, source, target, depth=0):
        if depth > 128: raise ValueError('Folder nesting is too deep')
        self.progress(0, source)
        info = fs.info(source)
        if info['link']: raise ValueError('Copying symbolic links is not supported: ' + source)
        if info['directory']:
            fs.mkdir(target)
            for entry in fs.listing(source): self._copy_tree(fs, entry['path'], join(target, entry['name']), depth + 1)
        elif not info.get('regular', True): raise ValueError('Special files cannot be copied')
        elif not split(target)[0]:
            with open(target, 'xb') as output:
                fs.read_to(source, output, self.progress)
                output.flush()
                os.fsync(output.fileno())
        elif not split(source)[0]:
            with open(source, 'rb') as input_file: fs.write_from(target, input_file, self.progress)
        else:
            # Remote-to-remote transfer spools to disk, never loads a whole file in RAM.
            with tempfile.TemporaryFile(dir=self._archive_scratch) as spool:
                fs.read_to(source, spool, self.staging_progress)
                spool.seek(0)
                fs.write_from(target, spool, self.progress)

    def _copy(self, fs, source, destination):
        if self.copy_resume is not None: return self.copy_resume.copy(fs, source, destination)
        skey, spath = split(source)
        dkey, dpath = split(destination)
        name = Path(spath).name
        target = join(destination, name)
        if skey == dkey:
            s = os.path.realpath(spath) if not skey else spath
            d = os.path.realpath(dpath) if not dkey else dpath
            if d == s or d.startswith(s.rstrip('/') + '/'):
                raise ValueError('Cannot copy a folder into itself')
        if moving.identity(fs, source) == moving.identity(fs, target):
            raise ValueError('Source and destination are the same item. Choose another folder.')
        record = self.replacement.prepare(fs, source, target) if self.replacement else None
        if not self.replacement and fs.exists(target): raise FileExistsError(name + ' already exists in the other panel. Rename it first.')
        temporary = join(destination, '.fileexplorer-' + uuid.uuid4().hex + '.partial')
        try:
            self._copy_tree(fs, source, temporary)
            self.progress(0, source)
            if self.replacement: target = self.replacement.publish(fs, temporary, target, record)
            else: fs.rename(temporary, target)
            return target
        finally:
            try:
                if fs.exists(temporary): fs.remove(temporary, lambda *_: None)
            except Exception: pass  # A disconnected share can retain the clearly named partial item.

    def _extract(self, fs, source, destination):
        if split(destination)[0]: raise ValueError('Extract into a local folder, then copy it to the share')
        name = archive.extraction_name(source)
        target = join(destination, name)
        if fs.exists(target): raise FileExistsError('Extraction folder already exists: ' + name)
        stage = tempfile.mkdtemp(prefix='.fileexplorer-extract-', dir=destination)
        try:
            with self._archive_file(fs, source, self.staging_progress) as local:
                archive.extract(local, stage, self.progress, self.extraction_limit())
            self.progress(0, source)
            fs.rename(stage, target)
            return target
        finally:
            if os.path.isdir(stage): shutil.rmtree(stage)

    def _copy_archive(self, fs, sources, destination):
        source = archive.parse(sources[0])[0]
        members = [archive.parse(p)[1] for p in sources]
        # A selected folder already includes its descendants.
        members = [p for p in members if not any(p.startswith(q + '/') for q in members if p != q)]
        names = [posixpath.basename(p) for p in members]
        if len(set(names)) != len(names): raise ValueError('Selected archive items have conflicting names')
        for name in names:
            if not self.replacement and fs.exists(join(destination, name)): raise FileExistsError(name + ' already exists in the other panel. Rename it first.')
        with tempfile.TemporaryDirectory(prefix='selected-', dir=self._archive_scratch) as stage:
            with self._archive_file(fs, source, self.staging_progress) as local:
                archive.extract(local, stage, self.staging_progress, self.extraction_limit(), selected=members)
            for member in members:
                out = self._copy(fs, str(Path(stage) / member), destination)
                with self.lock:
                    self.job['completed'] += 1
                    self.job['outputs'].append(out)

    def _empty_trash(self):
        return trash.empty(self.home, self.progress)

    def _trash(self, fs, source):
        if shutil.which('gio'):
            # GIO implements freedesktop trash on the item's own filesystem,
            # including removable media. It refuses when trash is unavailable.
            result = subprocess.run(['gio', 'trash', '--', source], capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise ValueError(result.stderr.strip() or 'Trash is unavailable for this location')
            return source
        # Freedesktop trash format, always in the user's home with original path metadata.
        trash = Path(self.home) / '.local/share/Trash'
        files, infos = trash / 'files', trash / 'info'
        files.mkdir(parents=True, exist_ok=True)
        infos.mkdir(parents=True, exist_ok=True)
        name = Path(source).name + '.' + uuid.uuid4().hex[:12]
        target = str(files / name)
        info = infos / (name + '.trashinfo')
        info.write_text('[Trash Info]\nPath=' + quote(os.path.abspath(source), safe='/') +
                        '\nDeletionDate=' + datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + '\n')
        try:
            if os.stat(source, follow_symlinks=False).st_dev != os.stat(files).st_dev:
                raise ValueError('Trash across filesystems is not supported. Move this item using Desktop Mode.')
            fs.rename(source, target)
            return target
        except Exception:
            info.unlink(missing_ok=True)
            raise

    def _work(self, action, sources, destination, options=None):
        fs = VFS(self.profiles())
        scratch = tempfile.TemporaryDirectory(prefix='.fileexplorer-worker-', dir=self.settings_dir)
        self._archive_scratch = scratch.name
        self._archive_work_files = {}
        try:
            self._plan(fs, action, sources, destination)
            if action == 'pack':
                def uploading(size):
                    with self.lock:
                        self.job['total_work'] = self.job['work_bytes'] + size
                        self.job['total_bytes'] += size
                output = packing.create(fs, self._packing_entries, destination, options, self._archive_scratch, self.progress, uploading)
                with self.lock: self.job.update(completed=len(sources), outputs=[output], status='done')
                return
            if action == 'empty_trash':
                self._empty_trash()
                with self.lock: self.job.update(completed=1, status='done')
                return
            virtual = [p for p in sources if archive.is_location(p)]
            for source in dict.fromkeys(archive.parse(p)[0] for p in virtual):
                self._copy_archive(fs, [p for p in virtual if archive.parse(p)[0] == source], destination)
            for source in sources:
                if archive.is_location(source): continue
                self.progress(0, source)
                if action == 'copy': out = self._copy(fs, source, destination)
                elif action == 'move':
                    def verifying(n, name):
                        self.staging_progress(n, name)
                        with self.lock: self.job['phase'] = 'Moving / verifying'
                    out = moving.move(fs, source, destination, self._copy, verifying, self.replacement)
                elif action == 'extract': out = self._extract(fs, source, destination)
                elif action == 'trash': out = self._trash(fs, source)
                else:
                    fs.remove(source, self.progress)
                    out = source
                with self.lock:
                    self.job['completed'] += 1
                    self.job['outputs'].append(out)
            with self.lock: self.job['status'] = 'done'
        except Cancelled as e:
            with self.lock: self.job.update(status='cancelled', error=str(e))
        except Exception as e:
            with self.lock: self.job.update(status='error', error=error_message(e))
        finally:
            self._archive_work_files = None
            fs.close()
            scratch.cleanup()

    def shutdown(self):
        self.media.shutdown()
        self.cancel.set()
        self.executor.shutdown(wait=True, cancel_futures=True)


def error_message(error):
    # pysmb exceptions can include protocol packet dumps. Do not expose them.
    if error.__class__.__module__.startswith(('smb', 'nmb')):
        return 'SMB operation failed. Check the connection, permissions and credentials.'
    if isinstance(error, PermissionError): return 'Permission denied. FileExplorer runs as your Steam user.'
    # Socket failures can escape pysmb as built-in exceptions. Keep this neutral:
    # RPC and worker callers also handle non-SMB operations, not all resumable.
    if isinstance(error, (ConnectionError, TimeoutError)):
        return 'Connection unavailable or interrupted. Check the network and server, then try again.'
    return str(error)[:500] or type(error).__name__
