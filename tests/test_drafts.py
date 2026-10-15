import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fileexplorer.drafts import Drafts
from fileexplorer.service import Service


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.service = Service(self.root, self.root / 'settings')
        self.file = self.root / 'file.json'
        self.original = b'{\r\n\t"value": 1\r\n}\r\n'
        self.file.write_bytes(self.original)
        self.info = self.service.read_text(str(self.file))

    def tearDown(self): self.service.shutdown(); self.temp.cleanup()

    def save(self, text):
        return self.service.drafts.save(str(self.file), text, self.info['revision'], self.info['encoding'], {'anchor': 2, 'head': 5})

    def test_incomplete_json_restores_after_restart_without_touching_original(self):
        self.save('{\n\t"value": unfinished')
        fresh = Drafts(self.root / 'settings')
        draft = fresh.read(str(self.file))
        self.assertEqual(draft['text'], '{\n\t"value": unfinished')
        self.assertEqual(draft['revision'], self.info['revision'])
        self.assertEqual(draft['cursor'], {'anchor': 2, 'head': 5})
        self.assertEqual(self.file.read_bytes(), self.original)
        if os.name == 'posix': self.assertEqual(fresh.path(str(self.file)).stat().st_mode & 0o777, 0o600)

    def test_atomic_write_failure_retains_last_acknowledged_draft(self):
        self.save('first')
        with patch('fileexplorer.drafts.os.replace', side_effect=OSError('power-cut')):
            with self.assertRaises(OSError): self.save('second')
        self.assertEqual(self.service.drafts.read(str(self.file))['text'], 'first')
        self.assertFalse(list(self.service.drafts.root.glob('.draft-*')))

    def test_recovery_uses_original_revision_and_does_not_overwrite_external_edit(self):
        self.save('{"value": 2}')
        self.file.write_text('{"external": true}')
        draft = self.service.drafts.read(str(self.file))
        with self.assertRaisesRegex(ValueError, 'changed outside'):
            self.service.save_text(str(self.file), draft['text'], draft['revision'], draft['encoding'])
        self.assertEqual(self.file.read_text(), '{"external": true}')

    def test_restored_text_save_keeps_original_encoding_and_line_endings(self):
        self.save(self.info['text'].replace('1', '42'))
        draft = self.service.drafts.read(str(self.file))
        self.service.save_text(str(self.file), draft['text'], draft['revision'], draft['encoding'])
        self.assertEqual(self.file.read_bytes(), self.original.replace(b'1', b'42'))
        self.service.drafts.discard(str(self.file))
        self.assertIsNone(self.service.drafts.read(str(self.file)))

    def test_invalid_metadata_oversize_and_cursor_are_rejected(self):
        for text, revision, encoding, cursor in [('x' * (512 * 1024 + 1), self.info['revision'], 'utf-8', {'anchor': 0, 'head': 0}),
                ('text', '../path', 'utf-8', {'anchor': 0, 'head': 0}), ('text', self.info['revision'], 'invalid', {'anchor': 0, 'head': 0}),
                ('text', self.info['revision'], 'utf-8', {'anchor': -1, 'head': 0})]:
            with self.assertRaises(ValueError): self.service.drafts.save(str(self.file), text, revision, encoding, cursor)
        self.assertIsNone(self.service.drafts.read(str(self.file)))
        self.save('😀')
        self.assertEqual(self.service.drafts.read(str(self.file))['cursor'], {'anchor': 2, 'head': 2})
