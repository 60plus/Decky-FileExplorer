"""Explicit conflict choices and staged replacement without deleting the old data first."""
from pathlib import Path
import uuid

from .vfs import join, parent, split, validate_name


def stamp(info):
    return {k: info.get(k) for k in ('directory', 'link', 'regular', 'size', 'modified')}


def snapshot(fs, root, progress=lambda *_: None):
    result = {}
    def visit(path, relative, depth):
        if depth > 128 or len(result) >= 100000:
            raise ValueError('The existing folder is too large or deeply nested to replace safely.')
        progress(0, path)
        info = fs.info(path)
        if info['link'] or not info['directory'] and not info.get('regular', True):
            raise ValueError('Replacing symbolic links or special files is not supported.')
        result[relative] = stamp(info)
        if info['directory']:
            for entry in fs.listing(path):
                visit(entry['path'], relative + '/' + entry['name'] if relative else entry['name'], depth + 1)
    visit(root, '', 0)
    return result


def child(root, relative):
    for part in relative.split('/') if relative else []:
        root = join(root, part)
    return root


def backup_path(fs, target):
    name = Path(split(target)[1]).name
    for number in range(1, 10001):
        suffix = '.bak' + (f'.{number}' if number > 1 else '')
        shortened = name
        while len((shortened + suffix).encode('utf-8')) > 255:
            shortened = shortened[:-1]
        candidate = join(parent(target), shortened + suffix)
        if not fs.exists(candidate): return candidate
    raise ValueError('Too many backup names already exist in this folder.')


def choose(fs, source, target, ask, progress=lambda *_: None):
    if not fs.exists(target): return None
    if ask is None: raise FileExistsError('Destination already exists. Choose how to handle the conflict.')
    before = snapshot(fs, target, progress)
    backup = backup_path(fs, target)
    choice = ask(dict(id=uuid.uuid4().hex, source=source, target=target,
                      backup=backup, directory=before['']['directory'], size=before['']['size']))
    if choice == 'resume': return choose(fs, source, target, ask, progress)
    if isinstance(choice, dict) and choice.get('choice') == 'rename':
        renamed = join(parent(target), validate_name(choice.get('name')))
        if renamed == target: raise ValueError('Choose a different name for the incoming item.')
        return dict(mode='rename', target=renamed)
    if choice not in ('backup', 'overwrite'):
        raise ValueError('Invalid conflict choice')
    return dict(mode=choice, old=backup, entries=before, phase='planned')


def apply_choice(record, publication):
    if publication and publication['mode'] == 'rename':
        record['output'] = publication['target']
        record.pop('publication', None)
    elif publication:
        record['publication'] = publication


def remove_old(fs, root, entries):
    """Only remove the recorded tree; tolerate our own interrupted cleanup."""
    if not fs.exists(root): return
    current = snapshot(fs, root)
    for relative, info in current.items():
        old = entries.get(relative)
        if old is None or info['directory'] != old['directory'] or not info['directory'] and info != old:
            raise ValueError('The previous destination changed. Its remaining backup was kept at: ' + root)
    for relative in sorted(current, key=lambda p: (p.count('/') + bool(p), p), reverse=True):
        path = child(root, relative)
        # Ancestors are checked again, so a replaced symlink is never followed.
        cursor = root
        for part in relative.split('/')[:-1] if relative else []:
            info = fs.info(cursor)
            if info['link'] or not info['directory']: raise ValueError('Backup folder changed; remaining data was kept: ' + root)
            cursor = join(cursor, part)
        if relative:
            info = fs.info(cursor)
            if info['link'] or not info['directory']: raise ValueError('Backup folder changed; remaining data was kept: ' + root)
        info = fs.info(path)
        if info['link'] or info['directory'] != current[relative]['directory'] or stamp(info) != current[relative] and not info['directory']:
            raise ValueError('Backup changed; remaining data was kept: ' + root)
        fs.remove_one(path, info['directory'])


def publish(fs, stage, target, record, save, ask=None, progress=lambda *_: None):
    """Journal old-name and new-name transitions; all renames refuse collisions."""
    target = record.get('output', target)
    publication = record.get('publication')
    if publication is None:
        publication = choose(fs, record['source'], target, ask, progress)
        if publication is None:
            try: fs.rename(stage, target)
            except Exception:
                if fs.exists(stage) and fs.exists(target):
                    return publish(fs, stage, target, record, save, ask, progress)
                raise
            return target
        apply_choice(record, publication)
        save(record)
        if publication['mode'] == 'rename':
            return publish(fs, stage, target, record, save, ask, progress)
    old = publication['old']
    if publication['phase'] == 'planned':
        if fs.exists(target) and snapshot(fs, target, progress) != publication['entries']:
            record.pop('publication'); save(record)
            return publish(fs, stage, target, record, save, ask, progress)
        if fs.exists(old) and fs.exists(target) and fs.exists(stage) and snapshot(fs, target, progress) == publication['entries']:
            # Someone used the suggested .bak name while the question was open.
            old = publication['old'] = backup_path(fs, target)
            save(record)
        if fs.exists(old):
            # Recover a crash between renaming the old target and journalling it.
            if fs.exists(target) or snapshot(fs, old, progress) != publication['entries']:
                raise ValueError('Destination or backup changed. Data was kept; check: ' + old)
        else:
            if not fs.exists(target) or snapshot(fs, target, progress) != publication['entries']:
                # A queue may have waited a long time. Ask again about the new item.
                record.pop('publication')
                save(record)
                return publish(fs, stage, target, record, save, ask, progress)
            fs.rename(target, old)
        publication['phase'] = 'parked'; save(record)
    if publication['phase'] == 'parked':
        if fs.exists(stage):
            try:
                fs.rename(stage, target)
            except Exception:
                # Restore the original when publication fails, unless another file arrived.
                if not fs.exists(target) and fs.exists(old):
                    fs.rename(old, target)
                    publication['phase'] = 'planned'; save(record)
                raise
        elif not fs.exists(target):
            raise ValueError('The new copy is missing. The previous destination is kept at: ' + old)
        publication['phase'] = 'installed'; save(record)
    if publication['phase'] == 'installed':
        if publication['mode'] == 'overwrite': remove_old(fs, old, publication['entries'])
        publication['phase'] = 'complete'; save(record)
    return target


class Interaction:
    """A worker waits for an explicit per-conflict response, also with the UI closed."""
    def __init__(self, folder, service):
        self.folder, self.service = Path(folder), service

    def ask(self, conflict):
        import json
        from .jobs import atomic_json
        from .service import Cancelled
        response = self.folder / 'conflict-response.json'
        response.unlink(missing_ok=True)
        atomic_json(self.folder / 'conflict.json', conflict)
        with self.service.lock:
            self.service.job.update(conflict=conflict, phase='Waiting for conflict choice', speed=0)
        try:
            while not self.service.cancel.wait(.15):
                try: answer = json.loads(response.read_text())
                except FileNotFoundError: continue
                if answer.get('id') != conflict['id']: continue
                choice = answer.get('choice')
                if choice == 'cancel':
                    with self.service.lock: self.service.job['kept_for_later'] = True
                    raise Cancelled('Cancelled at a name conflict. Existing destination items were kept.')
                if choice == 'rename': return dict(choice='rename', name=validate_name(answer.get('name')))
                if choice in ('overwrite', 'backup', 'resume'): return choice
            raise Cancelled('Cancelled at a name conflict. Existing destination items were kept.')
        finally:
            with self.service.lock: self.service.job.pop('conflict', None)
            (self.folder / 'conflict.json').unlink(missing_ok=True)
            response.unlink(missing_ok=True)


class Replacement:
    def __init__(self, folder, ask, progress):
        self.folder, self.ask, self.progress = Path(folder), ask, progress

    def prepare(self, fs, source, target):
        record = dict(source=source, target=target, journal=uuid.uuid4().hex)
        publication = choose(fs, source, target, self.ask, self.progress)
        apply_choice(record, publication)
        self.save(record)
        return record

    def save(self, record):
        from .jobs import atomic_json
        atomic_json(self.folder / ('replacement-' + record['journal'] + '.json'), record)

    def publish(self, fs, stage, target, record):
        return publish(fs, stage, target, record, self.save, self.ask, self.progress)
