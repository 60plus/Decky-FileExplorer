import errno
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fileexplorer import conflicts, moving
from fileexplorer.copy_resume import CopyResume
from fileexplorer.service import Service, Cancelled
from fileexplorer.vfs import VFS


class ConflictTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.left, self.right = self.root/'left', self.root/'right'
        self.left.mkdir(); self.right.mkdir()
        self.source = self.left/'Document.txt'; self.source.write_bytes(b'new contents')
        self.target = self.right/self.source.name; self.target.write_bytes(b'old contents')
        self.fs = VFS({}); self.journal = self.root/'copy.jsonl'

    def tearDown(self):
        self.fs.close(); self.temp.cleanup()

    def copy(self, choice='backup', ask=None):
        return CopyResume(self.journal, lambda *_: None, ask or (lambda _: choice)).copy(self.fs, str(self.source), str(self.right))

    def test_backup_copy_preserves_old_and_source(self):
        self.copy()
        self.assertEqual(self.target.read_bytes(), b'new contents')
        self.assertEqual((self.right/'Document.txt.bak').read_bytes(), b'old contents')
        self.assertEqual(self.source.read_bytes(), b'new contents')

    def test_rename_incoming_copy_keeps_both_items_and_records_output(self):
        result = self.copy(dict(choice='rename', name='Second document.txt'))
        self.assertEqual(result, str(self.right/'Second document.txt'))
        self.assertEqual(Path(result).read_bytes(), b'new contents')
        self.assertEqual(self.target.read_bytes(), b'old contents')
        self.assertEqual(self.source.read_bytes(), b'new contents')
        self.copy(ask=lambda _: self.fail('Completed renamed copy should verify without asking'))

    def test_renamed_copy_resumes_after_interruption(self):
        def crash(size, _):
            if size: raise OSError('interrupted')
        with self.assertRaises(OSError):
            CopyResume(self.journal, crash, lambda _: dict(choice='rename', name='Saved.txt')).copy(self.fs, str(self.source), str(self.right))
        result = self.copy(ask=lambda _: self.fail('Rename must survive'))
        self.assertEqual(Path(result).name, 'Saved.txt')
        self.assertEqual(Path(result).read_bytes(), self.source.read_bytes())
        self.assertEqual(self.target.read_bytes(), b'old contents')

    def test_renamed_destination_collision_asks_again(self):
        other = self.right/'Second.txt'; other.write_bytes(b'keep other')
        calls = []
        def ask(info):
            calls.append(info['target'])
            return dict(choice='rename', name='Second.txt') if len(calls) == 1 else 'backup'
        result = self.copy(ask=ask)
        self.assertEqual(calls, [str(self.target), str(other)])
        self.assertEqual(result, str(other))
        self.assertEqual(other.read_bytes(), b'new contents')
        self.assertEqual(self.target.read_bytes(), b'old contents')
        self.assertEqual((self.right/'Second.txt.bak').read_bytes(), b'keep other')

    def test_rename_rejects_paths_and_unchanged_name(self):
        for name in ('../escape', '/tmp/escape', 'folder/name', '', '..', 'Document.txt'):
            with self.subTest(name=name), self.assertRaises(ValueError): self.copy(dict(choice='rename', name=name))
        self.assertEqual(self.target.read_bytes(), b'old contents')

    def test_selected_archive_copy_uses_the_same_conflict_choices(self):
        import zipfile
        from fileexplorer.archive import location
        packed = self.left/'Documents.zip'
        with zipfile.ZipFile(packed, 'w') as output: output.writestr('Document.txt', 'from archive')
        for choice in ('backup', 'overwrite', 'rename'):
            with self.subTest(choice=choice), tempfile.TemporaryDirectory(dir=self.root) as work:
                folder = Path(work); (folder/'Document.txt').write_text('old')
                service = Service(self.root, folder/'settings')
                answer = dict(choice='rename', name='Renamed.txt') if choice == 'rename' else choice
                service.replacement = conflicts.Replacement(folder, lambda _: answer, service.progress)
                try:
                    service.start('copy', [location(str(packed), 'Document.txt')], str(folder))
                    service.executor.submit(lambda: None).result(timeout=10)
                    state = service.job_state(); self.assertEqual(state['status'], 'done', state)
                    target = folder/('Renamed.txt' if choice == 'rename' else 'Document.txt')
                    self.assertEqual(target.read_text(), 'from archive')
                    if choice == 'rename': self.assertEqual((folder/'Document.txt').read_text(), 'old')
                    if choice == 'backup': self.assertEqual((folder/'Document.txt.bak').read_text(), 'old')
                finally: service.shutdown()

    def test_same_and_cross_disk_move_can_rename_incoming_item(self):
        for cross in (False, True):
            with self.subTest(cross=cross), tempfile.TemporaryDirectory(dir=self.root) as work:
                folder = Path(work); left = folder/'a'; left.mkdir(); right = folder/'b'; right.mkdir()
                source = left/'file'; source.write_bytes(b'new'); (right/'file').write_bytes(b'old')
                service = Service(folder, folder/'settings'); service.job = dict(action='move', bytes=0, work_bytes=0)
                replacement = conflicts.Replacement(folder, lambda _: dict(choice='rename', name='renamed'), lambda *_: None)
                rename = self.fs.rename
                def forced(a, b):
                    if cross and a == str(source): raise OSError(errno.EXDEV, 'different disk')
                    return rename(a, b)
                try:
                    with patch.object(self.fs, 'rename', side_effect=forced):
                        result = moving.move(self.fs, str(source), str(right), service._copy, lambda *_: None, replacement)
                    self.assertEqual(result, str(right/'renamed'))
                    self.assertFalse(source.exists()); self.assertEqual(Path(result).read_bytes(), b'new')
                    self.assertEqual((right/'file').read_bytes(), b'old')
                finally: service.shutdown()

    def test_overwrite_replaces_only_after_new_copy_is_ready(self):
        def ask(_):
            self.assertEqual(self.target.read_bytes(), b'old contents')
            return 'overwrite'
        self.copy(ask=ask)
        self.assertEqual(self.target.read_bytes(), b'new contents')
        self.assertEqual([p.name for p in self.right.iterdir()], ['Document.txt'])

    def test_backups_are_numbered_without_overwriting_an_earlier_backup(self):
        (self.right/'Document.txt.bak').write_bytes(b'previous backup')
        self.copy()
        self.assertEqual((self.right/'Document.txt.bak').read_bytes(), b'previous backup')
        self.assertEqual((self.right/'Document.txt.bak.2').read_bytes(), b'old contents')

    def test_backup_name_taken_while_waiting_uses_another_name(self):
        def ask(info):
            Path(info['backup']).write_bytes(b'other program')
            return 'backup'
        self.copy(ask=ask)
        self.assertEqual((self.right/'Document.txt.bak').read_bytes(), b'other program')
        self.assertEqual((self.right/'Document.txt.bak.2').read_bytes(), b'old contents')

    def test_cancel_does_not_modify_either_item(self):
        def ask(_): raise Cancelled('cancel')
        with self.assertRaises(Cancelled): self.copy(ask=ask)
        self.assertEqual(self.target.read_bytes(), b'old contents')
        self.assertEqual(self.source.read_bytes(), b'new contents')
        self.assertEqual(len(list(self.right.iterdir())), 1)

    def test_changed_destination_requires_a_fresh_choice(self):
        seen = []
        def ask(info):
            seen.append(info['id'])
            if len(seen) == 1: self.target.write_bytes(b'changed while waiting')
            return 'backup'
        self.copy(ask=ask)
        self.assertEqual(len(seen), 2)
        self.assertEqual((self.right/'Document.txt.bak').read_bytes(), b'changed while waiting')

    def test_destination_arriving_during_copy_is_asked_about(self):
        self.target.unlink(); seen = []
        def progress(n, _):
            if n and not self.target.exists(): self.target.write_bytes(b'arrived later')
        CopyResume(self.journal, progress, lambda item: seen.append(item) or 'backup').copy(self.fs, str(self.source), str(self.right))
        self.assertEqual(len(seen), 1)
        self.assertEqual((self.right/'Document.txt.bak').read_bytes(), b'arrived later')

    def test_same_item_cannot_be_replaced(self):
        with self.assertRaisesRegex(ValueError, 'same item'):
            CopyResume(self.journal, lambda *_: None, lambda _: self.fail('Must not ask')).copy(self.fs, str(self.source), str(self.left))
        self.assertTrue(self.source.exists())

    def test_folder_replacement_keeps_old_only_files_in_backup(self):
        self.source.unlink(); self.source.mkdir(); (self.source/'new.txt').write_text('new')
        self.target.unlink(); self.target.mkdir(); (self.target/'old.txt').write_text('old')
        self.copy()
        self.assertEqual([p.name for p in self.target.iterdir()], ['new.txt'])
        self.assertEqual((self.right/'Document.txt.bak/old.txt').read_text(), 'old')

    def test_overwrite_folder_cleans_up_old_tree(self):
        self.target.unlink(); self.target.mkdir(); (self.target/'nested').mkdir(); (self.target/'nested/old').write_text('old')
        self.copy('overwrite')
        self.assertEqual(self.target.read_bytes(), b'new contents')
        self.assertEqual(len(list(self.right.iterdir())), 1)

    def test_failure_before_publish_keeps_the_original(self):
        rename = self.fs.rename
        def fail(stage, target):
            if str(stage).endswith('.partial'): raise OSError('disk failure')
            return rename(stage, target)
        with patch.object(self.fs, 'rename', side_effect=fail), self.assertRaisesRegex(OSError, 'disk failure'):
            self.copy('overwrite')
        self.assertEqual(self.target.read_bytes(), b'old contents')
        self.copy('overwrite')
        self.assertEqual(self.target.read_bytes(), b'new contents')

    def test_power_loss_at_each_publish_rename_is_recoverable(self):
        for fail_at in (1, 2):
            with self.subTest(rename=fail_at), tempfile.TemporaryDirectory(dir=self.root) as work:
                dest = Path(work); target = dest/self.source.name; target.write_bytes(b'old contents')
                journal = dest/'journal'; renamed = 0; rename = self.fs.rename
                def crash(a, b):
                    nonlocal renamed
                    rename(a, b); renamed += 1
                    if renamed == fail_at: raise KeyboardInterrupt('simulated power loss')
                with patch.object(self.fs, 'rename', side_effect=crash), self.assertRaises(KeyboardInterrupt):
                    CopyResume(journal, lambda *_: None, lambda _: 'backup').copy(self.fs, str(self.source), str(dest))
                CopyResume(journal, lambda *_: None, lambda _: self.fail('Choice should survive')).copy(self.fs, str(self.source), str(dest))
                self.assertEqual(target.read_bytes(), b'new contents')
                self.assertEqual((dest/'Document.txt.bak').read_bytes(), b'old contents')

    def test_overwrite_cleanup_refuses_new_unrecorded_files(self):
        self.target.unlink(); self.target.mkdir(); (self.target/'old').write_text('old')
        rename = self.fs.rename
        def inject(a, b):
            rename(a, b)
            if str(a).endswith('.partial'): (self.right/'Document.txt.bak/unexpected').write_text('keep')
        with patch.object(self.fs, 'rename', side_effect=inject), self.assertRaisesRegex(ValueError, 'kept'):
            self.copy('overwrite')
        self.assertEqual((self.right/'Document.txt.bak/unexpected').read_text(), 'keep')
        self.assertEqual(self.target.read_bytes(), b'new contents')

    def test_old_copy_checkpoint_does_not_mistake_a_conflict_for_completion(self):
        self.target.unlink()
        rename = self.fs.rename
        def interrupted(a, b):
            self.target.write_bytes(b'external file')
            raise KeyboardInterrupt('before publish')
        with patch.object(self.fs, 'rename', side_effect=interrupted), self.assertRaises(KeyboardInterrupt): self.copy()
        self.copy()
        self.assertEqual(self.target.read_bytes(), b'new contents')
        self.assertEqual((self.right/'Document.txt.bak').read_bytes(), b'external file')

    def test_same_disk_and_cross_disk_move_backup_and_overwrite(self):
        for cross in (False, True):
            for choice in ('backup', 'overwrite'):
                with self.subTest(cross=cross, choice=choice), tempfile.TemporaryDirectory(dir=self.root) as work:
                    folder = Path(work); left = folder/'a'; left.mkdir(); right = folder/'b'; right.mkdir()
                    source = left/'file'; source.write_bytes(b'new'); (right/'file').write_bytes(b'old')
                    service = Service(folder, folder/'settings')
                    service.job = dict(action='move', bytes=0, work_bytes=0)
                    replacement = conflicts.Replacement(folder, lambda _: choice, lambda *_: None)
                    rename = self.fs.rename
                    def forced(a, b):
                        if cross and a == str(source): raise OSError(errno.EXDEV, 'different disk')
                        return rename(a, b)
                    try:
                        with patch.object(self.fs, 'rename', side_effect=forced):
                            result = moving.move(self.fs, str(source), str(right), service._copy, lambda *_: None, replacement)
                        self.assertFalse(source.exists()); self.assertEqual(Path(result).read_bytes(), b'new')
                        self.assertEqual((right/'file.bak').exists(), choice == 'backup')
                        if choice == 'backup': self.assertEqual((right/'file.bak').read_bytes(), b'old')
                    finally: service.shutdown()


if __name__ == '__main__': unittest.main()
