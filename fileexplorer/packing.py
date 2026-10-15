"""Streaming archive creation using SteamOS libarchive and bounded VFS reads."""
import ctypes as C
import ctypes.util
import os
from pathlib import Path
import tempfile
import uuid

from .copy_resume import CHUNK, read_at, signature
from .moving import inside, snapshot
from .vfs import join, split, validate_name

FORMATS = {
    'zip': ('ZIP', '.zip', 'zip', None),
    '7z': ('7z', '.7z', '7zip', None),
    'tar': ('TAR', '.tar', 'pax_restricted', None),
    'tar.gz': ('TAR + gzip', '.tar.gz', 'pax_restricted', 'gzip'),
    'tar.bz2': ('TAR + bzip2', '.tar.bz2', 'pax_restricted', 'bzip2'),
    'tar.xz': ('TAR + xz', '.tar.xz', 'pax_restricted', 'xz'),
}


def options(value):
    if not isinstance(value, dict) or set(value) != {'format', 'level', 'name'}:
        raise ValueError('Choose an archive format, compression level and file name')
    kind, level = value['format'], value['level']
    if kind not in FORMATS: raise ValueError('Unsupported archive format')
    if type(level) is not int or not 0 <= level <= 9: raise ValueError('Compression level must be between 0 and 9')
    if not isinstance(value['name'], str): raise ValueError('Enter an archive file name')
    name = validate_name(value['name'].strip())
    suffix = FORMATS[kind][1]
    if not name.lower().endswith(suffix): name = validate_name(name + suffix)
    return dict(format=kind, level=level, name=name)


def plan(fs, sources, destination, progress):
    entries, names = [], set()
    for source in sources:
        if inside(fs, destination, source): raise ValueError('Create the archive outside the selected folder')
        base = Path(split(source)[1]).name
        for path, relative, info in snapshot(fs, source, progress):
            name = base + ('/' + relative if relative else '')
            if name in names: raise ValueError('Selected items have conflicting archive names')
            if '\\' in name or any(p in ('.', '..') for p in name.split('/')): raise ValueError('File name is not portable inside archives')
            names.add(name); entries.append((path, name, info))
            if len(entries) > 100000: raise ValueError('Archive would contain more than 100,000 entries')
    return entries


def write(fs, entries, output, settings, progress):
    lib = C.CDLL(ctypes.util.find_library('archive') or 'libarchive.so.13')
    def bind(name, result, *args):
        fun = getattr(lib, name); fun.restype = result; fun.argtypes = list(args); return fun
    ptr, integer, string = C.c_void_p, C.c_int, C.c_char_p
    new = bind('archive_write_new', ptr)
    release = bind('archive_write_free', integer, ptr)
    close = bind('archive_write_close', integer, ptr)
    error = bind('archive_error_string', string, ptr)
    opening = bind('archive_write_open_fd', integer, ptr, integer)
    set_options = bind('archive_write_set_options', integer, ptr, string)
    header = bind('archive_write_header', integer, ptr, ptr)
    data_write = bind('archive_write_data', C.c_ssize_t, ptr, ptr, C.c_size_t)
    finish = bind('archive_write_finish_entry', integer, ptr)
    entry_new = bind('archive_entry_new', ptr)
    entry_free = bind('archive_entry_free', None, ptr)
    pathname = bind('archive_entry_set_pathname_utf8', None, ptr, string)
    size = bind('archive_entry_set_size', None, ptr, C.c_int64)
    kind = bind('archive_entry_set_filetype', None, ptr, C.c_uint)
    perm = bind('archive_entry_set_perm', None, ptr, integer)
    mtime = bind('archive_entry_set_mtime', None, ptr, C.c_int64, C.c_long)
    handle = new()
    def check(code):
        if code < 0: raise ValueError((error(handle) or b'Archive creation failed').decode(errors='replace'))
    try:
        _, _, format_name, compression = FORMATS[settings['format']]
        check(bind('archive_write_set_format_' + format_name, integer, ptr)(handle))
        level = settings['level']
        if compression:
            check(bind('archive_write_add_filter_' + compression, integer, ptr)(handle))
            check(set_options(handle, f'{compression}:compression-level={max(1, level) if compression == "bzip2" else level}'.encode()))
        elif format_name in ('zip', '7zip'):
            algorithm = 'store' if level == 0 else 'deflate' if format_name == 'zip' else 'lzma2'
            check(set_options(handle, f'{format_name}:compression={algorithm}'.encode()))
            if level: check(set_options(handle, f'{format_name}:compression-level={level}'.encode()))
        check(opening(handle, output.fileno()))
        for source, name, before in entries:
            progress(0, source)
            current = fs.info(source)
            if current['link'] or current['directory'] != before['directory'] or signature(current) != signature(before):
                raise ValueError('A source changed while packing. No finished archive was published.')
            entry = entry_new()
            try:
                pathname(entry, name.encode('utf-8'))
                kind(entry, 0o040000 if before['directory'] else 0o100000)
                perm(entry, before.get('mode', 0o755 if before['directory'] else 0o644) & 0o777)
                modified = before['modified'] / (1 if split(source)[0] else 1e9)
                mtime(entry, int(modified), 0)
                size(entry, 0 if before['directory'] else before['size'])
                check(header(handle, entry))
                offset = 0
                while not before['directory'] and offset < before['size']:
                    progress(0, source)
                    data = read_at(fs, source, offset, min(CHUNK, before['size'] - offset))
                    if not data: raise ValueError('Source file changed while packing')
                    written = data_write(handle, data, len(data)); check(written)
                    if written != len(data): raise ValueError('Archive writer did not accept all data')
                    offset += written; progress(written, source)
                if signature(fs.info(source)) != signature(before): raise ValueError('Source file changed while packing')
                check(finish(handle))
            finally: entry_free(entry)
        progress(0, settings['name'])
        check(close(handle))
        output.flush(); os.fsync(output.fileno())
        progress(0, settings['name'])
    finally: release(handle)


def create(fs, entries, destination, settings, scratch, progress, uploading):
    target = join(destination, settings['name'])
    if fs.exists(target): raise FileExistsError('Archive already exists. Choose another name.')
    remote = bool(split(destination)[0])
    fd, stage = tempfile.mkstemp(prefix='.fileexplorer-pack-', suffix='.partial', dir=scratch if remote else destination)
    upload = None
    try:
        with os.fdopen(fd, 'w+b') as output:
            write(fs, entries, output, settings, progress)
        if remote:
            upload = join(destination, '.fileexplorer-' + uuid.uuid4().hex + '.partial')
            uploading(os.path.getsize(stage))
            with open(stage, 'rb') as input_file: fs.write_from(upload, input_file, progress)
            progress(0, target); fs.rename(upload, target)
            upload = None
        else: fs.rename(stage, target)
        return target
    finally:
        if os.path.exists(stage): os.unlink(stage)
        if upload:
            try: fs.remove_one(upload, False)
            except Exception: pass  # Disconnected SMB can retain a named partial archive.
