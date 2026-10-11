"""Stable GitHub releases, verified downloads and one startup notice per OS boot."""
import copy
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import ssl
import stat
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = '60plus/Decky-FileExplorer'
WEB = 'https://github.com/' + REPO
LATEST = 'https://api.github.com/repos/' + REPO + '/releases/latest'
DOWNLOADS = WEB + '/releases/download/'
MAX_ZIP = 32 * 1024**2
MAX_EXPANDED = 128 * 1024**2


def installed_version():
    return json.loads((Path(__file__).resolve().parents[1] / 'package.json').read_text())['version']


def version_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise ValueError('Unsupported stable release version.')
    return tuple(map(int, value.removeprefix('v').split('.')))


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if (target.scheme != 'https' or target.username or target.password or target.port not in (None, 443)
                or target.hostname not in ('github.com', 'api.github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com')):
            raise RuntimeError('GitHub redirected the download to an unexpected server.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_url(url, limit):
    if url != LATEST and not url.startswith(DOWNLOADS):
        raise ValueError('Update URL is outside the FileExplorer repository.')
    trust = Path('/etc/ssl/cert.pem')
    context = ssl.create_default_context(cafile=str(trust) if trust.is_file() else None)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), SafeRedirect())
    request = urllib.request.Request(url, headers={'User-Agent': 'FileExplorer-updater', 'Accept': 'application/vnd.github+json'})
    try:
        with opener.open(request, timeout=25) as response:
            if int(response.headers.get('Content-Length', '0')) > limit:
                raise RuntimeError('Update download is too large.')
            data = response.read(limit + 1)
            if len(data) > limit: raise RuntimeError('Update download is too large.')
            return data
    except urllib.error.HTTPError as error:
        if error.code == 404 and url == LATEST: return None
        if error.code in (403, 429): raise RuntimeError('GitHub is limiting requests. Try again later.') from error
        raise RuntimeError('Could not download the release from GitHub.') from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError('Cannot reach GitHub. Check the connection and try again.') from error


def asset_url(asset, tag):
    expected = DOWNLOADS + urllib.parse.quote(tag, safe='') + '/' + urllib.parse.quote(asset['name'], safe='')
    if asset.get('browser_download_url') != expected:
        raise ValueError('Release asset is outside the expected repository or release.')
    return expected


def check_release(installed):
    raw = read_url(LATEST, 2 * 1024**2)
    if raw is None: return dict(installed=installed, latest=None, candidate=None, message='No public stable release is available yet.')
    release = json.loads(raw)
    if not isinstance(release, dict) or release.get('draft') or release.get('prerelease'):
        raise ValueError('GitHub did not return a stable release.')
    tag = release['tag_name']
    key = version_key(tag)
    version = tag.removeprefix('v')
    if release.get('html_url') != WEB + '/releases/tag/' + tag:
        raise ValueError('Release belongs to an unexpected repository.')
    result = dict(installed=installed, latest=version, candidate=None, message='You have the latest version.' if key == version_key(installed) else 'Your installed version is newer than the latest release.')
    if key <= version_key(installed): return result
    filename = f'FileExplorer-{version}.zip'
    assets = release.get('assets', [])
    def one(name):
        matches = [a for a in assets if a.get('name') == name]
        if len(matches) != 1: raise ValueError('The release is missing its plugin ZIP or checksum.')
        return matches[0]
    asset, checksum = one(filename), one(filename + '.sha256')
    if type(asset.get('size')) is not int or not 0 < asset['size'] <= MAX_ZIP:
        raise ValueError('Invalid release asset size.')
    url = asset_url(asset, tag)
    checksum_bytes = read_url(asset_url(checksum, tag), 1024)
    match = re.fullmatch(r'([a-fA-F0-9]{64})  ' + re.escape(filename) + r'\r?\n?', checksum_bytes.decode('ascii'))
    if not match: raise ValueError('Invalid release checksum file.')
    digest = match[1].lower()
    if asset.get('digest') and asset['digest'] != 'sha256:' + digest:
        raise ValueError('Release checksum does not match GitHub asset metadata.')
    result.update(message='Update available.', candidate=dict(version=version, url=url, sha256=digest,
                  size=asset['size'], notes=str(release.get('body') or '')[:16000], release_url=release['html_url']))
    return result


def verify_archive(data, candidate):
    if len(data) != candidate['size'] or hashlib.sha256(data).hexdigest() != candidate['sha256']:
        raise ValueError('The update ZIP failed its checksum check.')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > 10000 or sum(i.file_size for i in infos) > MAX_EXPANDED:
                raise ValueError('The update ZIP is too large when extracted.')
            names = set()
            for item in infos:
                path = PurePosixPath(item.filename)
                mode = stat.S_IFMT(item.external_attr >> 16)
                if (not item.filename.startswith('FileExplorer/') or '\\' in item.filename or ':' in item.filename
                        or '..' in path.parts or item.filename.rstrip('/') != path.as_posix()
                        or mode not in (0, stat.S_IFREG, stat.S_IFDIR) or item.filename in names):
                    raise ValueError('The update ZIP contains an unsafe path or file.')
                names.add(item.filename)
            prefix = 'FileExplorer/'
            package = json.loads(archive.read(prefix + 'package.json'))
            plugin = json.loads(archive.read(prefix + 'plugin.json'))
            if (package.get('version') != candidate['version'] or package.get('name') != 'decky-fileexplorer'
                    or plugin.get('name') != 'FileExplorer' or plugin.get('author') != '60plus'):
                raise ValueError('The update contains a different plugin or version.')
            if package.get('remote_binary') or plugin.get('remote_binary'):
                raise ValueError('Updates must include their dependencies in the verified ZIP.')
            for name in ('main.py', 'dist/index.js', 'fileexplorer/service.py', 'fileexplorer/updates.py', 'vendor/smb/SMBConnection.py'):
                if prefix + name not in names: raise ValueError('The update is missing required plugin files.')
            if archive.testzip(): raise ValueError('The update ZIP is damaged.')
    except (zipfile.BadZipFile, KeyError, UnicodeError) as error:
        raise ValueError('The update ZIP has invalid package metadata.') from error


def atomic_write(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.update-')
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data); file.flush(); os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


class Updates:
    def __init__(self, service):
        self.service = service
        self.root = service.settings_dir / 'updates'
        self.root.mkdir(mode=0o700, exist_ok=True)
        self.lock = threading.RLock()
        self.result = None
        self.checked_at = 0

    def check(self):
        with self.lock:
            if self.result is not None and time.monotonic() - self.checked_at < 30:
                return copy.deepcopy(self.result)
            self.result = None
            result = check_release(installed_version())
            self.result, self.checked_at = result, time.monotonic()
            return copy.deepcopy(result)

    def prepare(self, version):
        with self.lock:
            candidate = (self.result or {}).get('candidate')
            if not candidate or candidate['version'] != version:
                raise ValueError('Check for updates again before downloading.')
            data = read_url(candidate['url'], MAX_ZIP)
            verify_archive(data, candidate)
            target = self.root / ('FileExplorer-' + candidate['sha256'] + '.zip')
            atomic_write(target, data)
            for previous in self.root.glob('FileExplorer-*.zip'):
                if previous != target and re.fullmatch(r'FileExplorer-[a-f0-9]{64}\.zip', previous.name): previous.unlink()
            return dict(artifact=target.as_uri(), version=candidate['version'], sha256=candidate['sha256'])

    def startup(self):
        with self.service.lock:
            if not self.service.config['settings'].get('check_updates_on_start', True): return None
        # Persist the Linux boot ID so plugin/Steam reloads cannot repeat the notice.
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        with self.lock, (self.root / 'startup.lock').open('a') as lockfile:
            fcntl.flock(lockfile, fcntl.LOCK_EX)
            path = self.root / 'startup.json'
            try: state = json.loads(path.read_text())
            except (FileNotFoundError, ValueError): state = {}
            if state.get('boot') != boot: state = {'boot': boot}
            if state.get('checked') or state.get('retry_after', 0) > time.time(): return None
            try:
                result = self.check()
            except Exception:
                # A disconnected startup is not a successful check. Retry quietly.
                state['retry_after'] = time.time() + 300
                atomic_write(path, json.dumps(state).encode())
                return None
            with self.service.lock:
                if not self.service.config['settings'].get('check_updates_on_start', True): return None
            state.update(checked=True, notified=bool(result['candidate']))
            atomic_write(path, json.dumps(state).encode())
            return result['candidate']
