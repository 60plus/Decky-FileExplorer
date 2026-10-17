"""Streaming libarchive extraction into a fresh, private directory.

Never asks libarchive to write files: paths, types and byte limits are checked
here before writing. Links, devices, absolute names and traversal are rejected.
"""
import ctypes as C
import ctypes.util
import os
import base64
import posixpath
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit


def is_location(value):
    return isinstance(value, str) and value.startswith('archive://')


def extraction_name(source):
    from .vfs import split
    name = Path(split(source)[1]).name
    for extension in ('.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'):
        if name.lower().endswith(extension):
            name = name[:-len(extension)]
            break
    return name or 'Extracted'


def location(source, member=''):
    from .vfs import split
    split(source)
    token = base64.urlsafe_b64encode(source.encode()).decode().rstrip('=')
    return 'archive://' + token + '/' + quote(member, safe='/')


def parse(value):
    from .vfs import split
    u = urlsplit(value)
    if u.scheme != 'archive' or not u.netloc or u.query or u.fragment:
        raise ValueError('Invalid archive path')
    try:
        source = base64.b64decode(u.netloc + '=' * (-len(u.netloc) % 4), altchars=b'-_', validate=True).decode()
    except (ValueError, UnicodeError): raise ValueError('Invalid archive path')
    split(source)  # Nested virtual archives are deliberately not accepted.
    member = unquote(u.path.lstrip('/'))
    if member: member = safe_member(member).as_posix()
    return source, member


def parent(value):
    from .vfs import parent as folder_parent
    source, member = parse(value)
    return location(source, posixpath.dirname(member)) if member else folder_parent(source)


def safe_member(name: str) -> Path:
    name = name.replace('\\', '/')
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or ':' in name or '\x00' in name:
        raise ValueError('Unsafe archive entry: ' + name[:120])
    return Path(*p.parts)


def size_limit_error(limit, remote=False):
    subject = 'Remote archive' if remote else 'Archive'
    return ValueError(f'{subject} exceeds extraction size limit ({limit / 1024**3:g} GiB). '
                      'Increase Extraction limit in Settings or choose Unlimited.')


def _walk(source, destination=None, progress=lambda *_: None, limit=100 * 1024**3, selected=None):
    lib = C.CDLL(ctypes.util.find_library('archive') or 'libarchive.so.13')
    def bind(name, restype, *args):
        f = getattr(lib, name)
        f.restype, f.argtypes = restype, list(args)
        return f
    ptr, integer, string = C.c_void_p, C.c_int, C.c_char_p
    new = bind('archive_read_new', ptr)
    support_filter = bind('archive_read_support_filter_all', integer, ptr)
    support_format = bind('archive_read_support_format_all', integer, ptr)
    support_raw = bind('archive_read_support_format_raw', integer, ptr)
    archive_format = bind('archive_format', integer, ptr)
    opening = bind('archive_read_open_filename', integer, ptr, string, C.c_size_t)
    header = bind('archive_read_next_header', integer, ptr, C.POINTER(ptr))
    pathname = bind('archive_entry_pathname', string, ptr)
    kind = bind('archive_entry_filetype', C.c_uint, ptr)
    hardlink = bind('archive_entry_hardlink', string, ptr)
    symlink = bind('archive_entry_symlink', string, ptr)
    size = bind('archive_entry_size', C.c_int64, ptr)
    mtime = bind('archive_entry_mtime', C.c_int64, ptr)
    read = bind('archive_read_data', C.c_ssize_t, ptr, ptr, C.c_size_t)
    error = bind('archive_error_string', string, ptr)
    free = bind('archive_read_free', integer, ptr)
    handle = new()
    def check(code):
        if code < 0:
            raise ValueError((error(handle) or b'Archive could not be read').decode(errors='replace'))
    total, count, entries = 0, 0, {}
    try:
        check(support_filter(handle))
        check(support_format(handle))
        # libarchive's "all" excludes single compressed streams. Enable raw
        # fallback only for known compression headers, never for arbitrary data.
        with open(source, 'rb') as source_file: magic = source_file.read(6)
        if magic.startswith((b'\x1f\x8b', b'BZh', b'\xfd7zXZ\x00')): check(support_raw(handle))
        check(opening(handle, os.fsencode(source), 1024 * 128))
        entry = ptr()
        buffer = C.create_string_buffer(1024 * 1024)
        while True:
            rc = header(handle, C.byref(entry))
            if rc == 1: break
            check(rc)
            count += 1
            if count > 100000: raise ValueError('Archive contains more than 100,000 entries')
            raw_stream = archive_format(handle) == 0x90000
            name = 'data' if raw_stream else os.fsdecode(pathname(entry) or b'')
            relative = safe_member(name)
            if hardlink(entry) or symlink(entry) or kind(entry) not in (0o100000, 0o040000):
                raise ValueError('Archive contains a link or special file: ' + name[:120])
            normalized = relative.as_posix()
            if normalized == '.':
                if kind(entry) == 0o040000: continue
                raise ValueError('Invalid archive entry')
            progress(0, name)
            if destination is None:
                directory = kind(entry) == 0o040000
                if normalized in entries and not (directory and entries[normalized]['directory']):
                    raise ValueError('Archive contains duplicate entries: ' + name[:120])
                length = max(0, size(entry))
                if raw_stream:
                    length = 0
                    while True:
                        progress(0, name)
                        n = read(handle, buffer, len(buffer)); check(n)
                        if not n: break
                        length += n
                        if limit is not None and length > limit: raise size_limit_error(limit)
                entries[normalized] = dict(directory=directory, size=length, modified=mtime(entry))
                for p in relative.parents:
                    if str(p) == '.': break
                    key = p.as_posix()
                    if key in entries and not entries[key]['directory']: raise ValueError('Conflicting archive paths')
                    entries.setdefault(key, dict(directory=True, size=0, modified=0))
                continue
            if selected is not None and not any(normalized == s or normalized.startswith(s + '/') for s in selected):
                continue
            target = Path(destination) / relative
            if kind(entry) == 0o040000:
                target.mkdir(parents=True, exist_ok=True)
                continue
            if limit is not None and size(entry) > limit - total: raise size_limit_error(limit)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                while True:
                    progress(0, name)
                    n = read(handle, buffer, len(buffer))
                    check(n)
                    if not n: break
                    total += n
                    if limit is not None and total > limit: raise size_limit_error(limit)
                    output.write(buffer.raw[:n])
                    progress(n, name)
        return entries if destination is None else count
    finally:
        free(handle)


def manifest(source, limit=100 * 1024**3, progress=lambda *_: None):
    return _walk(source, limit=limit, progress=progress)


def extract(source, destination, progress, limit=100 * 1024**3, selected=None):
    if selected is not None:
        selected = [safe_member(s).as_posix() for s in selected]
        if not selected or '.' in selected: raise ValueError('Select archive contents first')
    return _walk(source, destination, progress, limit, selected)
