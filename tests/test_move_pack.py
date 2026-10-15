import errno
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from fileexplorer import archive, moving, packing
from fileexplorer.service import Service, Cancelled
from fileexplorer.vfs import VFS


class MovePackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.left, self.right = self.root/'left', self.root/'right'
        self.left.mkdir(); self.right.mkdir()
        self.service = Service(self.root, self.root/'settings')
        self.fs = VFS({})

    def tearDown(self):
        self.service.shutdown(); self.fs.close(); self.temp.cleanup()

    def sample(self):
        tree = self.left/'Folder ü'; tree.mkdir()
        (tree/'empty').mkdir(); (tree/'.hidden').write_bytes(b'\x00test\xff' * 1000)
        (tree/'script.sh').write_text('#!/bin/sh\necho hello\n'); (tree/'script.sh').chmod(0o755)
        return tree

    def job(self, action, sources, options=None):
        self.service.start(action, [str(p) for p in sources], str(self.right), options)
        for _ in range(1000):
            result = self.service.job_state()
            if result['status'] != 'running': return result
            time.sleep(.01)
        self.fail('Job timed out')

    def test_move_same_filesystem_is_rename_and_preserves_mode(self):
        source = self.sample(); inode = source.stat().st_ino
        result = self.job('move', [source]); self.assertEqual(result['status'], 'done', result)
        self.assertFalse(source.exists())
        dest = self.right/source.name
        self.assertEqual(dest.stat().st_ino, inode)
        self.assertEqual((dest/'script.sh').stat().st_mode & 0o777, 0o755)

    def force_cross(self, source):
        rename = self.fs.rename
        def cross(a, b):
            if a == str(source): raise OSError(errno.EXDEV, 'Another disk')
            return rename(a, b)
        return patch.object(self.fs, 'rename', side_effect=cross)

    def copy(self, fs, source, dest):
        self.service.job = dict(action='move', bytes=0, work_bytes=0)
        return self.service._copy(fs, source, dest)

    def test_cross_filesystem_move_verifies_then_deletes(self):
        source = self.sample()
        with self.force_cross(source):
            target = moving.move(self.fs, str(source), str(self.right), self.copy, lambda *_: None)
        self.assertFalse(source.exists())
        self.assertEqual((Path(target)/'.hidden').read_bytes(), b'\x00test\xff' * 1000)
        self.assertEqual((Path(target)/'script.sh').stat().st_mode & 0o777, 0o755)

    def test_cross_move_keeps_source_when_destination_is_corrupted(self):
        source = self.sample()
        def corrupted(fs, src, dest):
            target = self.copy(fs, src, dest)
            (Path(target)/'.hidden').write_bytes(b'x' * 6000)
            return target
        with self.force_cross(source), self.assertRaisesRegex(ValueError, 'verification'):
            moving.move(self.fs, str(source), str(self.right), corrupted, lambda *_: None)
        self.assertTrue((source/'.hidden').exists()); self.assertTrue((source/'script.sh').exists())

    def test_cross_move_keeps_new_source_files(self):
        source = self.sample()
        def changed(fs, src, dest):
            target = self.copy(fs, src, dest)
            (source/'created-during-copy').write_text('new data')
            return target
        with self.force_cross(source), self.assertRaisesRegex(ValueError, 'Folder changed'):
            moving.move(self.fs, str(source), str(self.right), changed, lambda *_: None)
        self.assertEqual((source/'created-during-copy').read_text(), 'new data')

    def test_cancellation_after_copy_keeps_sources(self):
        source = self.sample()
        def cancellation(n, name):
            if n: raise Cancelled('cancel')
        with self.force_cross(source), self.assertRaises(Cancelled):
            moving.move(self.fs, str(source), str(self.right), self.copy, cancellation)
        self.assertTrue((source/'.hidden').exists())

    def test_conflicts_and_nested_moves_are_rejected(self):
        source = self.sample(); (self.right/source.name).mkdir()
        result = self.job('move', [source]); self.assertEqual(result['status'], 'error')
        self.assertTrue(source.exists())
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.service.start('move', [str(source)], str(source/'empty'))
        with self.assertRaisesRegex(ValueError, 'parent folder'):
            self.service.start('move', [str(source), str(source/'.hidden')], str(self.right))

    def test_all_archive_formats_roundtrip_at_three_levels(self):
        source = self.sample()
        for format in packing.FORMATS:
            for level in (0, 5, 9):
                with self.subTest(format=format, level=level):
                    name = format.replace('.', '-') + str(level)
                    result = self.job('pack', [source], dict(format=format, level=level, name=name))
                    self.assertEqual(result['status'], 'done', result)
                    target = result['outputs'][0]
                    with tempfile.TemporaryDirectory(dir=self.root) as output:
                        archive.extract(target, output, lambda *_: None)
                        tree = Path(output)/source.name
                        self.assertEqual((tree/'.hidden').read_bytes(), (source/'.hidden').read_bytes())
                        self.assertEqual((tree/'script.sh').read_bytes(), (source/'script.sh').read_bytes())
                        self.assertTrue((tree/'empty').is_dir())
        self.assertTrue(source.exists())

    def test_packing_conflict_does_not_overwrite(self):
        source = self.sample(); (self.right/'existing.zip').write_bytes(b'keep')
        result = self.job('pack', [source], dict(format='zip', level=5, name='existing'))
        self.assertEqual(result['status'], 'error')
        self.assertEqual((self.right/'existing.zip').read_bytes(), b'keep')

    def test_pack_rejects_symlink_and_invalid_options(self):
        source = self.sample(); (source/'link').symlink_to(source/'.hidden')
        result = self.job('pack', [source], dict(format='zip', level=5, name='test'))
        self.assertEqual(result['status'], 'error')
        self.assertFalse((self.right/'test.zip').exists())
        for settings in [dict(format='rar', level=5, name='test'), dict(format='zip', level=True, name='test'), dict(format='zip', level=5, name='../test')]:
            with self.assertRaises(ValueError): packing.options(settings)

    def test_pack_cancel_removes_unfinished_output(self):
        source = self.sample()
        entries = packing.plan(self.fs, [str(source)], str(self.right), lambda *_: None)
        def cancel(n, name):
            if n: raise Cancelled('cancel')
        with self.assertRaises(Cancelled):
            packing.create(self.fs, entries, str(self.right), packing.options(dict(format='zip', level=5, name='test')), str(self.root), cancel, lambda *_: None)
        self.assertEqual(list(self.right.iterdir()), [])


if __name__ == '__main__': unittest.main()
