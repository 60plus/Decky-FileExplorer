"""Copy checkpoints: private staging, verified prefixes, no overwrite on retry."""
import hashlib
import io
import json
import os
import posixpath
import re
from pathlib import Path
import uuid

from .vfs import join, split, parent
from .durable import sync_directory
from . import conflicts

CHUNK = 1024 * 1024


def read_at(fs, location, offset, count):
    key, path = split(location)
    if key:
        conn, share = fs.remote(key)
        output = io.BytesIO()
        conn.retrieveFileFromOffset(share, path, output, offset=offset, max_length=count, timeout=30)
        return output.getvalue()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try: return os.pread(fd, count, offset)
    finally: os.close(fd)


def write_at(fs, location, offset, data):
    key, path = split(location)
    if key:
        conn, share = fs.remote(key)
        conn.storeFileFromOffset(share, path, io.BytesIO(data), offset=offset, truncate=False, timeout=30)
    else:
        fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
        try:
            with os.fdopen(fd, 'r+b') as output:
                output.seek(offset); output.write(data); output.flush(); os.fsync(output.fileno())
        except Exception:
            raise


def signature(info): return [info['size'], info['modified']]


class CopyResume:
    def __init__(self, path, progress, ask=None):
        self.path, self.progress = Path(path), progress
        self.ask = ask
        self.records = {}
        if self.path.exists():
            with self.path.open('rb+') as journal:
                while True:
                    offset = journal.tell(); line = journal.readline()
                    if not line: break
                    # A crash can leave only the final append incomplete.
                    if not line.endswith(b'\n'): journal.truncate(offset); break
                    event = json.loads(line)
                    source, kind, value = event['source'], event['kind'], event['value']
                    if kind == 'root':
                        old = self.records.setdefault(source, dict(files={}, directories=[]))
                        self.records[source] = dict(files=old['files'], directories=old['directories'], **value)
                    elif kind == 'file': self.records[source]['files'][event['relative']] = value
                    elif kind == 'directory': self.records[source]['directories'].append(value)

    def save(self, record, kind='root', relative=None):
        value = record['files'][relative] if kind == 'file' else relative if kind == 'directory' else {k: v for k, v in record.items() if k not in ('files', 'directories')}
        event = dict(source=record['source'], kind=kind, relative=relative, value=value)
        # Append one checkpoint, rather than rewriting a huge folder manifest.
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'ab') as journal:
            journal.write((json.dumps(event) + '\n').encode()); journal.flush(); os.fsync(journal.fileno())
        sync_directory(self.path.parent)

    def discard(self, fs, sources, destination):
        """Delete only recorded staging trees, never published outputs or sources.

        Preflight every tree before deleting anything. Unknown files, links or
        edited journal paths cause refusal rather than a recursive wildcard delete.
        """
        planned = []
        for source, record in self.records.items():
            stage = record['stage']
            key, path = split(stage)
            name = posixpath.basename(path)
            if (source not in sources or record['target'] != join(destination, Path(split(source)[1]).name)
                    or not re.fullmatch(r'\.fileexplorer-[a-f0-9]{32}\.partial', name)
                    or stage != join(destination, name)):
                raise ValueError('Partial-copy record does not match this operation. Nothing was removed.')
            if not fs.exists(stage): continue  # Published targets are deliberately untouched.
            allowed = {p: True for p in record['directories']}
            allowed.update({p: False for p in record['files']})
            def inspect(location, relative='', depth=0):
                if depth > 128: raise ValueError('Partial folder nesting is too deep.')
                info = fs.info(location)
                if relative not in allowed or info['link'] or info['directory'] != allowed[relative] or not info.get('regular', True) and not info['directory']:
                    raise ValueError('Partial copy contains changed or unrecognized items. Nothing was removed.')
                if info['directory']:
                    for entry in fs.listing(location): inspect(entry['path'], relative + '/' + entry['name'], depth + 1)
                elif info['size'] > record['files'][relative]['signature'][0]:
                    raise ValueError('Partial file changed. Nothing was removed.')
                planned.append((stage, location, info))
            inspect(stage)
        for stage, location, before in planned:
            # Check ancestors again before each non-recursive removal.
            relative = split(location)[1][len(split(stage)[1]):].strip('/')
            ancestor = stage
            for part in relative.split('/')[:-1] if relative else []:
                info = fs.info(ancestor)
                if info['link'] or not info['directory']: raise ValueError('Partial folder changed during cleanup.')
                ancestor = join(ancestor, part)
            if location != stage:
                info = fs.info(ancestor)
                if info['link'] or not info['directory']: raise ValueError('Partial folder changed during cleanup.')
            now = fs.info(location)
            if now['link'] or now['directory'] != before['directory'] or not now['directory'] and signature(now) != signature(before):
                raise ValueError('Partial copy changed during cleanup. Remaining items were kept.')
            fs.remove_one(location, now['directory'])
        for record in self.records.values():
            publication = record.get('publication')
            output = record.get('output', record['target'])
            if parent(output) != parent(record['target']): raise ValueError('The copy destination changed.')
            if publication and publication['phase'] in ('planned', 'parked') and fs.exists(publication['old']) and not fs.exists(output):
                fs.rename(publication['old'], output)
        return len(planned)

    def copy(self, fs, source, destination):
        target = join(destination, Path(split(source)[1]).name)
        from .moving import identity
        if identity(fs, source) == identity(fs, target):
            raise ValueError('Source and destination are the same item. Choose another folder.')
        skey, spath = split(source); dkey, dpath = split(destination)
        if skey == dkey:
            a = os.path.realpath(spath) if not skey else spath
            b = os.path.realpath(dpath) if not dkey else dpath
            if b == a or b.startswith(a.rstrip('/') + '/'):
                raise ValueError('Cannot copy a folder into itself')
        record = self.records.get(source)
        if record is None:
            record = dict(source=source, target=target, stage=join(destination, '.fileexplorer-' + uuid.uuid4().hex + '.partial'), files={}, directories=[], ready=False, done=False)
            publication = conflicts.choose(fs, source, target, self.ask, self.progress)
            conflicts.apply_choice(record, publication)
            self.records[source] = record; self.save(record)
        if record['target'] != target: raise ValueError('The copy destination changed. Start a new copy.')
        target = record.get('output', target)
        if parent(target) != parent(record['target']): raise ValueError('The copy destination changed. Start a new copy.')
        completed = record['done'] or record['ready'] and not fs.exists(record['stage']) and fs.exists(target)
        actual = target if completed else record['stage']
        self.tree(fs, source, actual, record, '', completed)
        if not completed:
            record['ready'] = True; self.save(record)
            target = conflicts.publish(fs, record['stage'], target, record, self.save, self.ask, self.progress)
        elif record.get('publication') and record['publication']['phase'] != 'complete':
            target = conflicts.publish(fs, record['stage'], target, record, self.save, self.ask, self.progress)
        record['done'] = True; self.save(record)
        return target

    def tree(self, fs, source, target, record, relative, completed, depth=0):
        if depth > 128: raise ValueError('Folder nesting is too deep')
        self.progress(0, source)
        info = fs.info(source)
        if info['link'] or not info.get('regular', True) and not info['directory']:
            raise ValueError('Copying links and special files is not supported')
        if info['directory']:
            if relative not in record['directories']:
                if completed: raise ValueError('Source folder changed. Use Start again.')
                # Record intent before mkdir so a service interruption remains recoverable.
                if fs.exists(target): raise ValueError('Copy staging folder already exists unexpectedly.')
                record['directories'].append(relative); self.save(record, 'directory', relative)
            if not fs.exists(target):
                if completed: raise ValueError('A completed folder was removed. Use Start again.')
                fs.mkdir(target)
            existing = fs.info(target)
            if not existing['directory'] or existing['link']: raise ValueError('Copy staging folder changed. Use Start again.')
            entries = fs.listing(source)
            expected = {e['name'] for e in entries}
            if any(e['name'] not in expected for e in fs.listing(target)):
                raise ValueError('Source or destination folder changed. Use Start again.')
            for entry in entries:
                name = entry['name']
                self.tree(fs, entry['path'], join(target, name), record, relative + '/' + name, completed, depth + 1)
            return
        entry = record['files'].get(relative)
        if entry is None:
            if completed: raise ValueError('Source file changed. Use Start again.')
            if fs.exists(target): raise ValueError('Copy staging file already exists unexpectedly.')
            entry = dict(signature=signature(info), digest=None)
            record['files'][relative] = entry; self.save(record, 'file', relative)
        if entry['signature'] != signature(info): raise ValueError('A source file changed since the interrupted copy. Use Start again.')
        if not fs.exists(target):
            if completed or entry['digest']: raise ValueError('A completed file was removed. Use Start again.')
            fs.write_from(target, io.BytesIO(), lambda *_: None)
        existing = fs.info(target)
        if existing['directory'] or existing['link'] or not existing.get('regular', True) or existing['size'] > info['size']:
            raise ValueError('A partial copy was changed. Use Start again.')
        if (completed or entry['digest']) and existing['size'] != info['size']:
            raise ValueError('A completed file was changed. Use Start again.')
        digest, offset = hashlib.sha256(), 0
        # Compare every saved byte before appending. Equal size alone is insufficient.
        while offset < existing['size']:
            self.progress(0, source)
            count = min(CHUNK, existing['size'] - offset)
            before = read_at(fs, source, offset, count)
            after = read_at(fs, target, offset, count)
            if len(before) != count or before != after: raise ValueError('A saved copy differs from its source. Use Start again.')
            digest.update(before); offset += count; self.progress(count, source)
        if entry['digest'] and digest.hexdigest() != entry['digest']:
            raise ValueError('A completed file changed. Use Start again.')
        while offset < info['size']:
            self.progress(0, source)
            data = read_at(fs, source, offset, min(CHUNK, info['size'] - offset))
            if not data: raise ValueError('Source file ended unexpectedly. Use Start again.')
            write_at(fs, target, offset, data)
            digest.update(data); offset += len(data); self.progress(len(data), source)
        if signature(fs.info(source)) != entry['signature']: raise ValueError('Source changed while copying. Use Start again.')
        entry['digest'] = digest.hexdigest(); self.save(record, 'file', relative)
