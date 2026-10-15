"""Small text files, exact encoding/EOL preservation and conflict-aware saves."""
import codecs
import difflib
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
from pathlib import Path

from . import archive
from .vfs import join, parent, split
from .durable import sync_directory

LIMIT = 512 * 1024
ENCODINGS = {'utf-8', 'utf-16-le', 'utf-16-be', 'cp1250', 'cp1252', 'latin-1'}


def read_bytes(fs, location):
    if archive.is_location(location): raise ValueError('Extract the file before editing it.')
    info = fs.info(location)
    if info['directory'] or info['link'] or not info.get('regular', True):
        raise ValueError('Only regular text files can be edited.')
    if info['size'] > LIMIT: raise ValueError('The text editor supports files up to 512 KiB.')
    output = io.BytesIO()
    received = 0
    def bounded(n, _):
        nonlocal received
        received += n
        if received > LIMIT: raise ValueError('The file grew beyond the editor limit.')
    fs.read_to(location, output, bounded)
    return output.getvalue()


def decode(raw, encoding=None):
    bom = b''
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        raise ValueError('UTF-32 is not supported by this editor.')
    for marker, codec in ((codecs.BOM_UTF8, 'utf-8'), (codecs.BOM_UTF16_LE, 'utf-16-le'), (codecs.BOM_UTF16_BE, 'utf-16-be')):
        if raw.startswith(marker):
            bom, encoding = marker, codec
            break
    encoding = encoding or 'utf-8'
    if encoding not in ENCODINGS: raise ValueError('Unsupported text encoding')
    try: text = raw[len(bom):].decode(encoding, errors='strict')
    except UnicodeError: raise ValueError('Cannot decode this file. Choose its original encoding; it will be kept when saving.')
    if '\0' in text or any(ord(c) < 32 and c not in '\t\r\n\f' for c in text):
        raise ValueError('This looks like a binary file and cannot be edited as text.')
    return text, encoding, bom


def normalize(text):
    return text.replace('\r\n', '\n').replace('\r', '\n')


def restore_endings(original, edited):
    """Keep individual old line endings; inserted lines use the prevailing style."""
    if '\r' in edited: raise ValueError('Editor text must use normalized line endings')
    before, after = normalize(original).split('\n'), edited.split('\n')
    endings = re.findall(r'\r\n|\r|\n', original)
    default = max(set(endings), key=endings.count) if endings else '\n'
    preserved = {}
    for kind, a, b, c, d in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
        if kind in ('equal', 'replace'):
            for offset in range(min(b - a, d - c)):
                if a + offset < len(endings): preserved[c + offset] = endings[a + offset]
    return ''.join(line + (preserved.get(i, default) if i < len(after) - 1 else '') for i, line in enumerate(after))


def read(fs, location, encoding=None):
    raw = read_bytes(fs, location)
    text, codec, bom = decode(raw, encoding)
    if normalize(text).count('\n') >= 10000: raise ValueError('The editor supports up to 10,000 lines.')
    endings = set(re.findall(r'\r\n|\r|\n', text))
    style = 'mixed' if len(endings) > 1 else {'\n': 'LF', '\r\n': 'CRLF', '\r': 'CR'}.get(next(iter(endings), ''), 'none')
    return dict(text=normalize(text), encoding=codec, bom=bool(bom), newline=style,
                revision=hashlib.sha256(raw).hexdigest(), name=Path(split(location)[1]).name, location=location)


def save(fs, location, text, revision, encoding=None):
    if not isinstance(text, str) or len(text) > LIMIT: raise ValueError('Edited text is too large')
    if text.count('\n') >= 10000: raise ValueError('The editor supports up to 10,000 lines.')
    if any(ord(c) < 32 and c not in '\t\n\f' for c in text): raise ValueError('Unsupported control character in edited text.')
    raw = read_bytes(fs, location)
    if hashlib.sha256(raw).hexdigest() != revision:
        raise ValueError('This file changed outside the editor. Reopen it before saving; your changes have not been written.')
    original, codec, bom = decode(raw, encoding)
    if Path(split(location)[1]).suffix.lower() == '.json':
        try:
            def reject(value): raise ValueError('Non-standard JSON value: ' + value)
            json.loads(text, parse_constant=reject)
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}')
        except ValueError as e: raise ValueError('Invalid JSON: ' + str(e))
    restored = restore_endings(original, text)
    try: data = bom + restored.encode(codec, errors='strict')
    except UnicodeError: raise ValueError('A character cannot be saved in the original encoding. The file was not changed.')
    if len(data) > LIMIT: raise ValueError('Edited file exceeds 512 KiB')
    if data == raw: return read(fs, location, codec)
    key, path = split(location)
    if key:
        token = uuid.uuid4().hex
        temporary = join(parent(location), '.fileexplorer-edit-' + token)
        backup = join(parent(location), '.fileexplorer-backup-' + token)
        moved = False
        try:
            fs.write_from(temporary, io.BytesIO(data), lambda *_: None)
            if read_bytes(fs, location) != raw: raise ValueError('The file changed before saving. Reopen it first.')
            fs.rename(location, backup); moved = True
            try: fs.rename(temporary, location)
            except Exception:
                try: fs.rename(backup, location); moved = False
                except Exception: raise ValueError('Save interrupted. The original is kept as ' + backup)
                raise
            fs.remove(backup, lambda *_: None); moved = False
        finally:
            try:
                if fs.exists(temporary): fs.remove(temporary, lambda *_: None)
            except Exception: pass
    else:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or not os.access(path, os.W_OK): raise PermissionError(path)
        fd, temporary = tempfile.mkstemp(prefix='.fileexplorer-edit-', dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, 'wb') as output:
                output.write(data); output.flush(); os.fsync(output.fileno())
            shutil.copystat(path, temporary, follow_symlinks=False)
            if hasattr(os, 'chown'):
                os.chown(temporary, info.st_uid, info.st_gid)
            if read_bytes(fs, location) != raw: raise ValueError('The file changed before saving. Reopen it first.')
            os.replace(temporary, path)
            sync_directory(os.path.dirname(path))
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    return read(fs, location, codec)
