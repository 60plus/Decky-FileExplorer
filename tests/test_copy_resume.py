import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fileexplorer.copy_resume import CopyResume
from fileexplorer.vfs import VFS


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        self.dest = self.root / 'destination'; self.dest.mkdir()
        self.journal = self.root / 'copy.jsonl'; self.fs = VFS({})
        self.data = bytes(range(256)) * 12000
        (self.source / 'large.bin').write_bytes(self.data)

    def tearDown(self): self.fs.close(); self.temp.cleanup()

    def interrupted(self):
        copied = 0
        def progress(n, _):
            nonlocal copied
            copied += n
            if copied >= 1024 * 1024: raise OSError('Connection lost')
        with self.assertRaisesRegex(OSError, 'Connection lost'):
            CopyResume(self.journal, progress).copy(self.fs, str(self.source), str(self.dest))
        record = CopyResume(self.journal, lambda *_: None).records[str(self.source)]
        self.assertFalse((self.dest / 'source').exists())
        self.assertEqual((Path(record['stage']) / 'large.bin').stat().st_size, 1024 * 1024)
        return record

    def test_resume_keeps_prefix_and_writes_only_remaining_bytes(self):
        record = self.interrupted()
        from fileexplorer.copy_resume import write_at
        with patch('fileexplorer.copy_resume.write_at', wraps=write_at) as writes:
            result = CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))
        self.assertEqual(Path(result, 'large.bin').read_bytes(), self.data)
        self.assertEqual(writes.call_args_list[0].args[2], 1024 * 1024)
        self.assertFalse(Path(record['stage']).exists())

    def test_changed_prefix_is_refused_without_overwriting(self):
        record = self.interrupted(); partial = Path(record['stage']) / 'large.bin'
        with partial.open('r+b') as f: f.write(b'altered')
        before = partial.read_bytes()
        with self.assertRaisesRegex(ValueError, 'differs'):
            CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))
        self.assertEqual(partial.read_bytes(), before)

    def test_changed_source_and_collisions_are_refused(self):
        self.interrupted(); (self.source / 'large.bin').write_bytes(b'new data')
        with self.assertRaisesRegex(ValueError, 'source file changed'):
            CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))
        fresh = self.root / 'fresh.json'; (self.dest / 'source').mkdir()
        with self.assertRaises(FileExistsError): CopyResume(fresh, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))

    def test_completed_files_are_verified_and_not_rewritten(self):
        CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))
        with patch('fileexplorer.copy_resume.write_at') as writes:
            CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))
        writes.assert_not_called()
        target = self.dest / 'source/large.bin'
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))

    def test_interruption_between_publish_and_journal_save(self):
        CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))
        checkpoint = CopyResume(self.journal, lambda *_: None)
        state = checkpoint.records[str(self.source)]; state['done'] = False
        checkpoint.save(state)
        self.assertEqual(CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest)), str(self.dest / 'source'))

    def test_symlink_partial_is_refused(self):
        record = self.interrupted(); partial = Path(record['stage']) / 'large.bin'
        partial.unlink(); partial.symlink_to(self.source / 'large.bin')
        with self.assertRaisesRegex(ValueError, 'partial copy'):
            CopyResume(self.journal, lambda *_: None).copy(self.fs, str(self.source), str(self.dest))
