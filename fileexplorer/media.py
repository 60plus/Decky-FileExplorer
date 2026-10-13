"""Read-only, capability-scoped loopback streaming. No files are exposed by path."""
import io
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import images
from .vfs import VFS, split

TYPES = json.loads(Path(__file__).with_name('media_types.json').read_text())
CHUNK = 256 * 1024
TAG_BUDGET = 8 * 1024 * 1024
TTL = 6 * 60 * 60
DEMUXERS = {'video/mp4': 'mov', 'video/webm': 'matroska', 'video/x-matroska': 'matroska', 'video/ogg': 'ogg',
            'audio/mp4': 'mov', 'audio/mpeg': 'mp3', 'audio/aac': 'aac', 'audio/wav': 'wav', 'audio/flac': 'flac', 'audio/ogg': 'ogg', 'audio/webm': 'matroska'}


def byte_range(value, size):
    if not value: return 0, size - 1, False
    if not value.startswith('bytes=') or ',' in value: raise ValueError('Invalid range')
    left, right = value[6:].split('-', 1)
    if not left:
        length = int(right)
        if length <= 0: raise ValueError('Invalid range')
        start, end = max(0, size - length), size - 1
    else:
        start, end = int(left), min(int(right), size - 1) if right else size - 1
    if start < 0 or start >= size or end < start: raise ValueError('Invalid range')
    return start, end, True


class Source:
    def __init__(self, location, profiles):
        self.location, self.profiles = location, profiles
        self.key, self.path = split(location)
        self.fd = None
        if self.key:
            fs = VFS(profiles)
            try:
                info = fs.info(location)
                if info['directory'] or info['link']: raise ValueError('Open a regular media file.')
                self.size = info['size']
            finally: fs.close()
        else:
            fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                os.close(fd)
                raise ValueError('Open a regular media file.')
            self.fd, self.size = fd, info.st_size
        if not self.size:
            self.close()
            raise ValueError('This media file is empty.')

    def read(self, offset, count, fs=None):
        count = min(count, max(0, self.size - offset))
        if not count: return b''
        if not self.key: return os.pread(self.fd, count, offset)
        conn, share = fs.remote(self.key)
        output = io.BytesIO()
        conn.retrieveFileFromOffset(share, self.path, output, offset=offset, max_length=count, timeout=15)
        return output.getvalue()

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


class TagReader:
    """Seekable metadata view with a total read budget, also for remote tags."""
    def __init__(self, source, fs):
        self.source, self.fs, self.offset, self.budget, self.calls = source, fs, 0, TAG_BUDGET, 256
        self.name = source.path

    def tell(self): return self.offset

    def seek(self, offset, whence=0):
        self.offset = offset + (self.offset if whence == 1 else self.source.size if whence == 2 else 0)
        if self.offset < 0: raise ValueError('Invalid metadata seek')
        return self.offset

    def read(self, count=-1):
        count = min(self.source.size - self.offset, count if count >= 0 else self.source.size)
        count = max(0, count)
        if count > self.budget or self.calls <= 0: raise ValueError('Metadata read budget exceeded')
        self.calls -= 1
        self.budget -= count
        result = self.source.read(self.offset, count, self.fs)
        self.offset += len(result)
        return result


def cover(source):
    """A missing, oversized or malformed tag never prevents playback."""
    fs = VFS(source.profiles)
    try:
        from tinytag import TinyTag
        tags = TinyTag.get(filename=source.path, file_obj=TagReader(source, fs), image=True, duration=False)
        picture = tags.images.any
        if picture and len(picture.data) <= TAG_BUDGET:
            return images.describe(picture.data)['data']
    except Exception:
        pass
    finally: fs.close()
    return None


def metadata(url, mime):
    """A bounded probe supplies a seek timeline when Steam cannot decode a file."""
    executable = shutil.which('ffprobe')
    if not executable: return dict(duration=None, has_video=False)
    from .jobs import systemd_environment
    try:
        result = subprocess.run([executable, '-v', 'error', '-protocol_whitelist', 'http,tcp',
                                 '-probesize', '2097152', '-analyzeduration', '1000000',
                                 '-f', DEMUXERS[mime], '-show_entries', 'format=duration:stream=codec_type', '-of', 'json', url],
                                env=systemd_environment(), stdin=subprocess.DEVNULL, capture_output=True, timeout=6)
        info = json.loads(result.stdout)
        try: value = float(info.get('format', {}).get('duration', 0))
        except (ValueError, TypeError): value = 0
        return dict(duration=value if math.isfinite(value) and 0 < value < 7 * 24 * 3600 else None,
                    has_video=any(stream.get('codec_type') == 'video' for stream in info.get('streams', [])))
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired): return dict(duration=None, has_video=False)


class Media:
    def __init__(self):
        self.lock = threading.RLock()
        self.sessions = {}
        self.server = None

    def open(self, location, profiles):
        if location.startswith('archive://'): raise ValueError('Extract this media file to a folder before playing it.')
        mime = TYPES.get(Path(split(location)[1]).suffix.lower().lstrip('.'))
        if not mime: raise ValueError('This media format is not supported.')
        source = Source(location, profiles)
        try:
            artwork = cover(source) if mime.startswith('audio/') else None
            with self.lock:
                self.prune()
                if len(self.sessions) >= 4: raise ValueError('Close another media player first.')
                if not self.server:
                    self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
                    self.server.media = self
                    threading.Thread(target=self.server.serve_forever, daemon=True, name='fileexplorer-media').start()
                token = secrets.token_urlsafe(32)
                self.sessions[token] = dict(source=source, mime=mime, touched=time.monotonic(), users=0, closed=False, processes=set())
                port = self.server.server_address[1]
                url = f'http://127.0.0.1:{port}/{token}'
            return dict(token=token, url=url, mime=mime, size=source.size, cover=artwork,
                        compatibility=bool(shutil.which('ffmpeg')), **metadata(url, mime))
        except Exception:
            source.close()
            raise

    def prune(self):
        for token, session in list(self.sessions.items()):
            if time.monotonic() - session['touched'] > TTL: self.close(token)

    def close(self, token):
        with self.lock:
            session = self.sessions.pop(token, None)
            if session:
                session['closed'] = True
                for process in session['processes']:
                    try: process.terminate()
                    except OSError: pass
                if not session['users']: session['source'].close()
        return True

    def shutdown(self):
        with self.lock:
            for token in list(self.sessions): self.close(token)
            server, self.server = self.server, None
        if server: server.shutdown(); server.server_close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass  # Tokens and file names must not enter HTTP logs.

    def do_HEAD(self): self.stream(False)
    def do_GET(self): self.stream(True)

    def stream(self, body):
        media = self.server.media
        authority = f'127.0.0.1:{self.server.server_address[1]}'
        if self.headers.get('Host') != authority:
            self.send_error(403)
            return
        request = urlsplit(self.path)
        compatibility = request.path.endswith('/compat')
        token = request.path[1:-7] if compatibility else self.path[1:]
        with media.lock:
            media.prune()
            session = media.sessions.get(token)
            if not session:
                self.send_error(404)
                return
            session['users'] += 1
            session['touched'] = time.monotonic()
        fs = VFS(session['source'].profiles)
        try:
            source = session['source']
            if compatibility:
                self.compatibility(session, token, request.query, body)
                return
            try: start, end, partial = byte_range(self.headers.get('Range'), source.size)
            except (ValueError, TypeError):
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{source.size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            self.send_response(206 if partial else 200)
            self.send_header('Content-Type', session['mime'])
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            if partial: self.send_header('Content-Range', f'bytes {start}-{end}/{source.size}')
            self.end_headers()
            if body:
                while start <= end and not session['closed']:
                    data = source.read(start, min(CHUNK, end - start + 1), fs)
                    if not data: break
                    self.wfile.write(data)
                    start += len(data)
                    session['touched'] = time.monotonic()
        except Exception: pass  # Never log paths, credentials or SMB protocol dumps.
        finally:
            fs.close()
            with media.lock:
                session['users'] -= 1
                if session['closed'] and not session['users']: source.close()

    def compatibility(self, session, token, query, body):
        executable = shutil.which('ffmpeg')
        try:
            args = parse_qs(query, strict_parsing=True)
            if set(args) - {'start', 'revision'}: raise ValueError()
            start = float(args.get('start', ['0'])[0])
            if not 0 <= start < 7 * 24 * 3600: raise ValueError()
        except (ValueError, TypeError): self.send_error(400); return
        if not executable: self.send_error(503); return
        media = self.server.media
        from .jobs import systemd_environment
        source_url = f'http://127.0.0.1:{self.server.server_address[1]}/{token}'
        command = [executable, '-hide_banner', '-loglevel', 'error', '-nostdin', '-threads', '2',
                   '-protocol_whitelist', 'http,tcp', '-f', DEMUXERS[session['mime']], '-ss', str(start), '-i', source_url,
                   '-map', '0:a:0?', '-sn', '-dn']
        if session['mime'].startswith('video/'):
            command += ['-map', '0:v:0', '-c:v', 'libvpx', '-deadline', 'realtime', '-cpu-used', '8',
                        '-threads', '2', '-filter_threads', '2', '-b:v', '1800k', '-vf',
                        "scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,format=yuv420p,fps=30"]
        else: command += ['-vn']
        command += ['-c:a', 'libopus', '-b:a', '128k', '-f', 'webm', '-cluster_time_limit', '500', 'pipe:1']
        process = None
        try:
            if body:
                with media.lock:
                    if session['closed']: self.send_error(410); return
                    # A seek cancels the old conversion rather than accumulating processes.
                    for previous in session['processes']:
                        try: previous.terminate()
                        except OSError: pass
                    process = subprocess.Popen(command, env=systemd_environment(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    session['processes'].add(process)
            self.send_response(200)
            self.send_header('Content-Type', 'video/webm' if session['mime'].startswith('video/') else 'audio/webm')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            if process:
                while not session['closed']:
                    data = process.stdout.read1(64 * 1024)
                    if not data: break
                    self.wfile.write(data)
                    session['touched'] = time.monotonic()
        finally:
            if process:
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
                process.stdout.close()
                with media.lock: session['processes'].discard(process)
