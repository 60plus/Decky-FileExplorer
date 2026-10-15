"""Private recovery drafts. Original files are only changed by explicit Save."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time

from .durable import sync_directory
from .editor import LIMIT, ENCODINGS
from .vfs import split


class Drafts:
    def __init__(self, settings):
        self.root = Path(settings) / 'drafts'
        self.root.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.root, 0o700)
        sync_directory(self.root.parent)
        self.lock = threading.RLock()

    def path(self, location):
        if not isinstance(location, str) or len(location) > 16384: raise ValueError('Invalid draft location')
        split(location)
        return self.root / (hashlib.sha256(location.encode()).hexdigest() + '.json')

    def read(self, location):
        with self.lock:
            path = self.path(location)
            if not path.exists(): return None
            if path.is_symlink() or path.stat().st_size > LIMIT * 8: raise ValueError('Invalid recovery draft')
            value = json.loads(path.read_text(encoding='utf-8'))
            if value.get('location') != location: raise ValueError('Recovery draft belongs to another file')
            return value

    def save(self, location, text, revision, encoding, cursor):
        if not isinstance(text, str) or len(text) > LIMIT or text.count('\n') >= 10000:
            raise ValueError('Recovery draft exceeds the editor limit')
        if not isinstance(revision, str) or not re.fullmatch('[a-f0-9]{64}', revision) or encoding not in ENCODINGS:
            raise ValueError('Invalid recovery draft metadata')
        if not isinstance(cursor, dict) or any(type(cursor.get(k)) is not int or cursor[k] < 0 for k in ('anchor', 'head')):
            raise ValueError('Invalid recovery cursor')
        # JS offsets use UTF-16 code units, including two units for emoji.
        length = len(text.encode('utf-16-le')) // 2
        value = dict(location=location, text=text, revision=revision, encoding=encoding,
                     cursor={k: min(cursor[k], length) for k in ('anchor', 'head')}, updated=time.time())
        with self.lock:
            path = self.path(location)
            fd, temporary = tempfile.mkstemp(prefix='.draft-', dir=self.root)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as output:
                    json.dump(value, output, ensure_ascii=False)
                    output.flush(); os.fsync(output.fileno())
                os.replace(temporary, path)
                sync_directory(self.root)
            finally:
                if os.path.exists(temporary): os.unlink(temporary)
        return True

    def discard(self, location):
        with self.lock:
            self.path(location).unlink(missing_ok=True)
            sync_directory(self.root)
        return True
