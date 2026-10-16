"""No-overwrite moves; cross-filesystem sources survive until verification."""
import errno
import hashlib
import os
import uuid
from pathlib import Path

from .copy_resume import CHUNK, read_at, signature
from .vfs import join, split


def identity(fs, location):
    key, path = split(location)
    if not key: return ('local', os.path.realpath(path))
    profile = fs.profiles[key]
    return ((profile['host'].lower(), profile.get('port', 445), profile['share'].lower()), path.casefold())


def inside(fs, child, parent):
    ck, cp = identity(fs, child); pk, pp = identity(fs, parent)
    return ck == pk and (cp == pp or cp.startswith(pp.rstrip('/') + '/'))


def snapshot(fs, source, progress):
    records = []
    def visit(path, relative, depth):
        if depth > 128 or len(records) >= 100000: raise ValueError('Too many files or nested folders')
        progress(0, path)
        info = fs.info(path)
        if info['link'] or not info.get('regular', True) and not info['directory']:
            raise ValueError('Links and special files cannot be moved across filesystems or packed')
        records.append((path, relative, info))
        if info['directory']:
            for entry in fs.listing(path):
                visit(entry['path'], relative + '/' + entry['name'] if relative else entry['name'], depth + 1)
    visit(source, '', 0)
    return records


def digest(fs, path, info, progress):
    result = hashlib.sha256(); offset = 0
    while offset < info['size']:
        progress(0, path)
        data = read_at(fs, path, offset, min(CHUNK, info['size'] - offset))
        if not data: raise ValueError('File changed while verifying the move. Source was kept.')
        result.update(data); offset += len(data); progress(len(data), path)
    if signature(fs.info(path)) != signature(info):
        raise ValueError('File changed while verifying the move. Source was kept.')
    return result.digest()


def move(fs, source, destination, copy_item, progress, replacement=None):
    if inside(fs, destination, source): raise ValueError('Cannot move a folder into itself')
    target = join(destination, Path(split(source)[1]).name)
    if identity(fs, source) == identity(fs, target):
        raise ValueError('Source and destination are the same item. Choose another folder.')
    record = replacement.prepare(fs, source, target) if replacement else None
    if not replacement and fs.exists(target): raise FileExistsError('Destination already exists. Rename it first.')
    # Same filesystem/share moves preserve metadata and do not copy file contents.
    if split(source)[0] == split(destination)[0]:
        try:
            progress(0, source)
            if replacement: target = replacement.publish(fs, source, target, record)
            else: fs.rename(source, target)
            return target
        except OSError as error:
            if error.errno != errno.EXDEV: raise
    records = snapshot(fs, source, progress)
    children = {}
    for _, rel, _ in records:
        if rel:
            parent, _, name = rel.rpartition('/')
            children.setdefault(parent, set()).add(name)
    final_target, staging = target, None
    if replacement:
        staging = join(destination, '.fileexplorer-' + uuid.uuid4().hex + '.move')
        fs.mkdir(staging)
    try:
        target = copy_item(fs, source, staging or destination)
    except BaseException:
        if staging:
            try: fs.remove_one(staging, True)
            except Exception: pass  # Keep any remaining contents and the original copy error.
        raise
    verified = []
    # Check all data before deleting even the first source file.
    for path, relative, before in records:
        out = target
        for component in relative.split('/') if relative else []: out = join(out, component)
        current, copied = fs.info(path), fs.info(out)
        if current['link'] or copied['link'] or current['directory'] != before['directory'] or copied['directory'] != before['directory']:
            raise ValueError('Source or destination changed during the move. Source was kept.')
        if before['directory']:
            expected = children.get(relative, set())
            if {e['name'] for e in fs.listing(path)} != expected or {e['name'] for e in fs.listing(out)} != expected:
                raise ValueError('Folder changed during the move. Source was kept.')
        else:
            if signature(current) != signature(before) or copied['size'] != before['size']:
                raise ValueError('File changed during the move. Source was kept.')
            if digest(fs, path, before, progress) != digest(fs, out, copied, progress):
                raise ValueError('Move verification failed. Source was kept.')
        verified.append((path, before))
    if not split(destination)[0] and not split(source)[0]:
        for _, relative, info in reversed(records):
            out = os.path.join(target, relative) if relative else target
            os.chmod(out, info['mode'] & 0o777)
            os.utime(out, ns=(info['modified'], info['modified']))
    if replacement:
        target = replacement.publish(fs, target, final_target, record)
        fs.remove_one(staging, True)
    for path, before in reversed(verified):
        progress(0, path)
        current = fs.info(path)
        if current['link'] or current['directory'] != before['directory'] or (not before['directory'] and signature(current) != signature(before)):
            raise ValueError('Source changed during cleanup. Remaining source files were kept.')
        if before['directory']:
            # Never recursively delete an unverified/newly created source file.
            if fs.listing(path): raise ValueError('Source folder is not empty. Remaining files were kept.')
        fs.remove_one(path, before['directory'])
    return target
