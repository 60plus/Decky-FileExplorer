import io
import os
import posixpath
import socket
import stat
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from .credentials import password_for
from .durable import sync_directory

CHUNK = 1024 * 1024


def validate_name(name):
    if not isinstance(name, str) or not name or name in ('.', '..') or any(c in name for c in '/\\\x00'):
        raise ValueError('Enter a file name without slashes')
    if len(name.encode('utf-8')) > 255: raise ValueError('File name is too long')
    return name


def split(location):
    if not isinstance(location, str) or '\x00' in location:
        raise ValueError('Invalid path')
    if location.startswith('smb://'):
        u = urlsplit(location)
        if u.query or u.fragment or not u.netloc: raise ValueError('Invalid share path')
        p = unquote(u.path)
        if '\\' in p or '..' in p.split('/'): raise ValueError('Invalid share path')
        return u.netloc, posixpath.normpath('/' + p.lstrip('/'))
    if not os.path.isabs(location): raise ValueError('An absolute path is required')
    return None, os.path.normpath(location)


def join(location, name):
    validate_name(name)
    share, path = split(location)
    return 'smb://' + share + quote(posixpath.join(path, name), safe='/') if share else os.path.join(path, name)


def parent(location):
    share, path = split(location)
    return 'smb://' + share + quote(posixpath.dirname(path), safe='/') if share else os.path.dirname(path)


class VFS:
    def __init__(self, profiles):
        self.profiles = profiles
        self.connections = {}

    def close(self):
        for conn in self.connections.values(): conn.close()

    def remote(self, key):
        if key not in self.profiles: raise ValueError('Saved connection not found. Add it in Locations.')
        profile = self.profiles[key]
        if key not in self.connections:
            from smb.SMBConnection import SMBConnection
            host = profile['host']
            conn = SMBConnection(profile.get('username', ''), password_for(key, profile),
                                 'FileExplorer', host.split('.')[0], domain=profile.get('domain', ''),
                                 use_ntlm_v2=True, is_direct_tcp=True)
            try:
                if not conn.connect(socket.gethostbyname(host), profile.get('port', 445), timeout=12):
                    raise ValueError('SMB login failed. Check username, password and domain.')
                if not conn.isUsingSMB2:
                    raise ValueError('This server only supports SMB1. Enable SMB2 on the server.')
            except Exception:
                conn.close()
                raise
            self.connections[key] = conn
        return self.connections[key], profile['share']

    def listing(self, location):
        key, path = split(location)
        result = []
        if key:
            conn, share = self.remote(key)
            for item in conn.listPath(share, path, timeout=20):
                if item.filename in ('.', '..'): continue
                validate_name(item.filename)
                result.append(dict(name=item.filename, path=join(location, item.filename),
                                   directory=item.isDirectory, link=False, size=item.file_size,
                                   modified=item.last_write_time, hidden=bool(item.file_attributes & 0x02) or item.filename.startswith('.')))
        else:
            with os.scandir(path) as entries:
                for item in entries:
                    try:
                        s = item.stat(follow_symlinks=False)
                        result.append(dict(name=item.name, path=item.path, directory=item.is_dir(),
                                           link=item.is_symlink(), size=s.st_size, modified=s.st_mtime,
                                           hidden=item.name.startswith('.'), executable=bool(s.st_mode & 0o111)))
                    except (FileNotFoundError, PermissionError): continue
        if len(result) > 50000: raise ValueError('More than 50,000 entries. Open a smaller folder.')
        return result

    def info(self, location):
        key, path = split(location)
        if key:
            conn, share = self.remote(key)
            item = conn.getAttributes(share, path, timeout=20)
            return dict(directory=item.isDirectory, link=False, size=item.file_size, modified=item.last_write_time)
        s = os.lstat(path)
        return dict(directory=stat.S_ISDIR(s.st_mode), link=stat.S_ISLNK(s.st_mode), size=s.st_size,
                    regular=stat.S_ISREG(s.st_mode), modified=s.st_mtime_ns, mode=stat.S_IMODE(s.st_mode))

    def remove_one(self, location, directory):
        """Remove exactly one verified item, never recurse into a changed folder."""
        key, path = split(location)
        if key:
            conn, share = self.remote(key)
            if directory: conn.deleteDirectory(share, path, timeout=20)
            else:
                if any(c in path for c in '*?'): raise ValueError('Cannot delete an SMB filename containing wildcards')
                conn.deleteFiles(share, path, timeout=20)
        else:
            if directory: os.rmdir(path)
            else: os.unlink(path)
            sync_directory(os.path.dirname(path))

    def exists(self, location):
        key, path = split(location)
        if not key: return os.path.lexists(path)
        # A failed SMB stat is not proof of absence (permission/network errors).
        name = posixpath.basename(path)
        return any(x['name'].casefold() == name.casefold() for x in self.listing(parent(location)))

    def mkdir(self, location):
        key, path = split(location)
        if key:
            conn, share = self.remote(key)
            conn.createDirectory(share, path, timeout=20)
        else:
            os.mkdir(path)
            sync_directory(os.path.dirname(path))

    def rename(self, source, target):
        key, path = split(source)
        key2, path2 = split(target)
        if key != key2: raise ValueError('Rename must stay on the same filesystem')
        if self.exists(target): raise FileExistsError('Destination already exists')
        if key:
            conn, share = self.remote(key)
            conn.rename(share, path, path2, timeout=30)
        else:
            # renameat2 NOREPLACE prevents a racing destination from being overwritten.
            if os.name == 'posix':
                import ctypes
                libc = ctypes.CDLL(None, use_errno=True)
                if libc.renameat2(-100, os.fsencode(path), -100, os.fsencode(path2), 1):
                    errno = ctypes.get_errno()
                    raise OSError(errno, os.strerror(errno))
            else: os.rename(path, path2)
            sync_directory(os.path.dirname(path2))
            if os.path.dirname(path) != os.path.dirname(path2): sync_directory(os.path.dirname(path))

    def remove(self, location, progress):
        info = self.info(location)
        progress(0, location)
        key, path = split(location)
        if info['directory'] and not info['link']:
            for entry in self.listing(location): self.remove(entry['path'], progress)
            if key:
                conn, share = self.remote(key)
                conn.deleteDirectory(share, path, timeout=20)
            else: os.rmdir(path)
        elif key:
            conn, share = self.remote(key)
            # pysmb's deleteFiles accepts wildcards: refuse such names.
            if any(c in path for c in '*?'): raise ValueError('Cannot delete an SMB filename containing wildcards')
            conn.deleteFiles(share, path, timeout=20)
        else: os.unlink(path)

    def read_to(self, location, output, progress):
        key, path = split(location)
        if key:
            conn, share = self.remote(key)
            class Sink:
                def write(self, data):
                    progress(len(data), location)
                    return output.write(data)
            conn.retrieveFile(share, path, Sink(), timeout=30)
        else:
            with open(path, 'rb') as source:
                while True:
                    progress(0, location)
                    data = source.read(CHUNK)
                    if not data: break
                    output.write(data)
                    progress(len(data), location)

    def write_from(self, location, source, progress):
        key, path = split(location)
        if key:
            conn, share = self.remote(key)
            class Reader:
                def read(self, count):
                    progress(0, location)
                    data = source.read(count)
                    progress(len(data), location)
                    return data
            conn.storeFile(share, path, Reader(), timeout=30)
        else:
            with open(path, 'xb') as output:
                while True:
                    progress(0, location)
                    data = source.read(CHUNK)
                    if not data: break
                    output.write(data)
                    progress(len(data), location)
                output.flush()
                os.fsync(output.fileno())
            sync_directory(os.path.dirname(path))
