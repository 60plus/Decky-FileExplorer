import io
import json
import os
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fileexplorer.service import Service
from fileexplorer.vfs import join, split, validate_name
from fileexplorer import archive, discovery, trash


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.left, self.right = self.home / 'left', self.home / 'right'
        self.left.mkdir(); self.right.mkdir()
        self.service = Service(self.home, self.root / 'settings')

    def tearDown(self):
        self.service.shutdown()
        self.temp.cleanup()

    def test_resumable_remote_copy_progress_reaches_all_thresholds(self):
        self.service.copy_resume = object()
        self.service.job = {}
        with patch.object(self.service, '_estimate_tree', return_value=100):
            self.service._plan(None, 'copy', ['smb://one/source'], 'smb://two/target')
        self.assertEqual(self.service.job['total_work'], 100)

    def test_appearance_persists_and_rejects_invalid_values(self):
        desired = dict(accent='violet', opacity=85, text_size=18, ui_scale=80)
        self.service.update_settings(desired)
        other = Service(self.home, self.root / 'settings')
        try:
            for key, value in desired.items(): self.assertEqual(other.state()['settings'][key], value)
        finally: other.shutdown()
        for key, value in [('accent', 'red;'), ('opacity', 0), ('opacity', True), ('text_size', 200), ('text_size', '18'), ('ui_scale', 0), ('ui_scale', True), ('ui_scale', '80'), ('ui_scale', 120)]:
            with self.assertRaises(ValueError): self.service.update_settings({key: value})
            self.assertEqual(self.service.state()['settings'][key], desired[key])

    def job(self, action, paths, destination=None):
        self.service.start(action, list(map(str, paths)), str(destination) if destination else None)
        for _ in range(400):
            state = self.service.job_state()
            if state['status'] != 'running': return state
            time.sleep(.01)
        self.fail('Job timed out')

    def test_copy_folder_preserves_bytes_hidden_and_unicode(self):
        source = self.left / 'Żółw'; source.mkdir()
        (source / '.hidden').write_bytes(bytes(range(256)) * 9000)
        state = self.job('copy', [source], self.right)
        self.assertEqual(state['status'], 'done', state)
        self.assertEqual((self.right / 'Żółw/.hidden').read_bytes(), (source / '.hidden').read_bytes())
        self.assertFalse(list(self.right.glob('.fileexplorer*')))

    def test_collision_never_overwrites(self):
        (self.left / 'a').write_text('new'); (self.right / 'a').write_text('keep')
        state = self.job('copy', [self.left / 'a'], self.right)
        self.assertEqual(state['status'], 'error')
        self.assertEqual((self.right / 'a').read_text(), 'keep')

    def test_copy_into_self_refused(self):
        (self.left / 'child').mkdir()
        self.assertEqual(self.job('copy', [self.left], self.left / 'child')['status'], 'error')

    @unittest.skipUnless(os.name == 'posix', 'Linux symlinks')
    def test_symlink_copy_rejected_and_partial_cleaned(self):
        (self.left / 'a').symlink_to(self.right, target_is_directory=True)
        self.assertEqual(self.job('copy', [self.left], self.right)['status'], 'error')
        self.assertEqual(list(self.right.iterdir()), [])

    @unittest.skipUnless(os.name == 'posix', 'Linux FIFO')
    def test_special_file_refused_without_hanging(self):
        os.mkfifo(self.left / 'pipe')
        self.assertEqual(self.job('copy', [self.left / 'pipe'], self.right)['status'], 'error')

    def test_hidden_and_sorting(self):
        (self.left / '.a').touch(); (self.left / 'z').mkdir(); (self.left / 'b').write_text('hello')
        self.assertEqual([e['name'] for e in self.service.list_dir(str(self.left))['entries']], ['z', 'b'])
        self.service.update_settings({'show_hidden': True})
        self.assertEqual([e['name'] for e in self.service.list_dir(str(self.left))['entries']], ['z', '.a', 'b'])

    def test_rename_collision_and_traversal(self):
        (self.left / 'a').write_text('a'); (self.left / 'b').write_text('b')
        with self.assertRaises(FileExistsError): self.service.rename(str(self.left / 'a'), 'b')
        for name in ('../escape', '', '.', '..', 'a/b', 'a\\b'):
            with self.assertRaises(ValueError): self.service.mkdir(str(self.left), name)

    def test_trash_and_metadata(self):
        source = self.left / 'delete me.txt'; source.write_text('recover me')
        with patch('fileexplorer.service.shutil.which', return_value=None):
            state = self.job('trash', [source])
        self.assertEqual(state['status'], 'done', state)
        self.assertFalse(source.exists())
        self.assertEqual(Path(state['outputs'][0]).read_text(), 'recover me')
        meta = next((self.home / '.local/share/Trash/info').iterdir()).read_text()
        self.assertIn('delete%20me.txt', meta)

    def test_root_protection(self):
        with self.assertRaises(ValueError): self.service.start('trash', [str(self.home)])

    def test_settings_survive_restart_without_password_leak(self):
        self.service.config['connections']['test'] = dict(host='server', share='files', label='Test', password='example-secret')
        self.service.update_settings({'show_hidden': True})
        s = Service(self.home, self.root / 'settings')
        try:
            self.assertTrue(s.state()['settings']['show_hidden'])
            self.assertNotIn('example-secret', json.dumps(s.state()))
            if os.name == 'posix': self.assertEqual(os.stat(s.config_file).st_mode & 0o777, 0o600)
        finally: s.shutdown()

    def test_legend_modes_persist_and_reject_unknown_values(self):
        for mode in ('panel', 'steam', 'both', 'none'):
            self.service.update_settings({'legend_mode': mode})
            fresh = Service(self.home, self.root / 'settings')
            try: self.assertEqual(fresh.state()['settings']['legend_mode'], mode)
            finally: fresh.shutdown()
        with self.assertRaises(ValueError): self.service.update_settings({'legend_mode': 'broken'})

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_zip_and_tar_extract(self):
        z = self.left / 'bundle.zip'
        with zipfile.ZipFile(z, 'w') as f: f.writestr('folder/żółw.txt', 'hello')
        state = self.job('extract', [z], self.right)
        self.assertEqual(state['status'], 'done', state)
        self.assertEqual((self.right / 'bundle/folder/żółw.txt').read_text(), 'hello')
        t = self.left / 'compressed.tar.gz'
        with tarfile.open(t, 'w:gz') as f:
            info = tarfile.TarInfo('a.txt'); info.size = 4; f.addfile(info, io.BytesIO(b'test'))
        self.assertEqual(self.job('extract', [t], self.right)['status'], 'done')
        self.assertEqual((self.right / 'compressed/a.txt').read_bytes(), b'test')

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_single_compressed_streams_browse_extract_and_enforce_limit(self):
        import gzip, bz2, lzma
        payload = b'Plain compressed text\n' * 100
        for suffix, compress in [('gz', gzip.compress), ('bz2', bz2.compress), ('xz', lzma.compress)]:
            source = self.left / ('payload.' + suffix); source.write_bytes(compress(payload))
            listing = self.service.list_dir(archive.location(str(source)))
            self.assertEqual([(e['name'], e['size']) for e in listing['entries']], [('data', len(payload))])
            target = self.right / suffix; target.mkdir()
            self.assertEqual(self.job('copy', [archive.location(str(source), 'data')], target)['status'], 'done')
            self.assertEqual((target / 'data').read_bytes(), payload)
            with self.assertRaisesRegex(ValueError, 'size limit'): archive.manifest(source, limit=100)
        fake = self.left / 'fake.rar'; fake.write_bytes(b'This is not an archive')
        with self.assertRaises(ValueError): archive.manifest(fake)

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_archive_traversal_rejected(self):
        z = self.left / 'bad.zip'
        with zipfile.ZipFile(z, 'w') as f: f.writestr('../escaped.txt', 'bad')
        self.assertEqual(self.job('extract', [z], self.right)['status'], 'error')
        self.assertFalse((self.right / 'escaped.txt').exists())
        self.assertEqual(list(self.right.iterdir()), [])

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_archive_symlink_rejected(self):
        t = self.left / 'link.tar'
        with tarfile.open(t, 'w') as f:
            info = tarfile.TarInfo('escape'); info.type = tarfile.SYMTYPE; info.linkname = '/tmp'; f.addfile(info)
        self.assertEqual(self.job('extract', [t], self.right)['status'], 'error')
        self.assertEqual(list(self.right.iterdir()), [])

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_archive_size_limit_cleans_stage(self):
        from fileexplorer.archive import extract
        z = self.left / 'limit.zip'
        with zipfile.ZipFile(z, 'w') as f: f.writestr('file.txt', 'x' * 1024)
        with self.assertRaises(ValueError): extract(z, self.right, lambda *_: None, limit=512)

    def test_unlimited_extraction_setting_persists_and_validates(self):
        self.service.update_settings({'extraction_limit_gib': 0})
        other = Service(self.home, self.root / 'settings')
        try:
            self.assertEqual(other.state()['settings']['extraction_limit_gib'], 0)
            self.assertIsNone(other.extraction_limit())
        finally: other.shutdown()
        for invalid in (-1, True, '0', 1001):
            with self.assertRaises(ValueError): self.service.update_settings({'extraction_limit_gib': invalid})
        self.service.update_settings({'extraction_limit_gib': 10})
        self.assertEqual(self.service.extraction_limit(), 10 * 1024**3)

    def test_remote_archive_limit_and_unlimited_in_both_download_paths(self):
        class Download:
            def info(self, _): return dict(directory=False, link=False, regular=True)
            def read_to(self, source, output, progress):
                output.write(b'test archive')
                # Simulate the transfer counter without allocating 2 GiB.
                progress(2 * 1024**3, source)
        self.service.staging_progress = lambda *_: None
        scratch = self.root / 'scratch'; scratch.mkdir()
        self.service._archive_scratch = str(scratch)
        source = 'smb://test/archive.zip'
        for worker_path in (False, True):
            self.service._archive_work_files = {} if worker_path else None
            self.service.update_settings({'extraction_limit_gib': 1})
            with self.assertRaisesRegex(ValueError, r'size limit \(1 GiB\).*Settings.*Unlimited'):
                with self.service._archive_file(Download(), source): pass
            self.service.update_settings({'extraction_limit_gib': 0})
            with self.service._archive_file(Download(), source) as downloaded:
                self.assertEqual(Path(downloaded).read_bytes(), b'test archive')

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_unlimited_whole_and_selected_extraction_keeps_path_checks(self):
        self.service.update_settings({'extraction_limit_gib': 0})
        z = self.left / 'unlimited.zip'
        with zipfile.ZipFile(z, 'w') as f: f.writestr('folder/file.txt', 'payload' * 1024)
        state = self.job('extract', [z], self.right)
        self.assertEqual(state['status'], 'done', state)
        selected = self.right / 'selected'; selected.mkdir()
        state = self.job('copy', [archive.location(str(z), 'folder')], selected)
        self.assertEqual(state['status'], 'done', state)
        self.assertEqual((selected / 'folder/file.txt').read_bytes(), (self.right / 'unlimited/folder/file.txt').read_bytes())
        bad = self.left / 'unsafe.zip'
        with zipfile.ZipFile(bad, 'w') as f: f.writestr('../outside.txt', 'bad')
        self.assertEqual(self.job('extract', [bad], self.right)['status'], 'error')
        self.assertFalse((self.right / 'outside.txt').exists())

    def test_cancel_preserves_original_and_removes_partial(self):
        source = self.left / 'large'; source.write_bytes(b'x' * 4_000_000)
        original_progress = self.service.progress
        def stop(n, name):
            if n: self.service.cancel.set()
            return original_progress(n, name)
        self.service.progress = stop
        self.assertEqual(self.job('copy', [source], self.right)['status'], 'cancelled')
        self.assertTrue(source.exists())
        self.assertEqual(list(self.right.iterdir()), [])

    def test_preview_binary_and_size_bound(self):
        p = self.left / 'binary'; p.write_bytes(b'a\x00b')
        self.assertIsNone(self.service.preview(str(p))['text'])
        p.write_bytes(b'x' * 300000)
        self.assertIsNone(self.service.preview(str(p))['text'])

    def test_smb_paths_roundtrip(self):
        p = join('smb://id/', 'żółw #100%.txt')
        self.assertEqual(split(p), ('id', '/żółw #100%.txt'))
        with self.assertRaises(ValueError): split('smb://id/../escape')

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_archive_navigation_and_selected_extraction(self):
        z = self.left / 'selection.zip'
        with zipfile.ZipFile(z, 'w') as f:
            f.writestr('folder/żółw.txt', 'selected')
            f.writestr('folder/.hidden', 'secret')
            f.writestr('other.txt', 'not selected')
            f.writestr('empty/', '')
        root = self.service.open_archive(str(z))['path']
        listing = self.service.list_dir(root)
        self.assertTrue(listing['archive'])
        self.assertEqual(listing['parent'], str(self.left))
        self.assertEqual([e['name'] for e in listing['entries']], ['empty', 'folder', 'other.txt'])
        folder = archive.location(str(z), 'folder')
        self.assertEqual([e['name'] for e in self.service.list_dir(folder)['entries']], ['żółw.txt'])
        self.assertEqual(self.service.list_dir(folder)['parent'], root)
        selected = archive.location(str(z), 'folder/żółw.txt')
        state = self.job('copy', [selected], self.right)
        self.assertEqual(state['status'], 'done', state)
        self.assertEqual((self.right / 'żółw.txt').read_text(), 'selected')
        self.assertFalse((self.right / 'folder').exists())
        self.assertFalse((self.right / 'other.txt').exists())
        state = self.job('copy', [folder, archive.location(str(z), 'empty')], self.right)
        self.assertEqual(state['status'], 'done', state)
        self.assertEqual((self.right / 'folder/.hidden').read_text(), 'secret')
        self.assertTrue((self.right / 'empty').is_dir())
        self.assertEqual(self.job('copy', [selected], self.right)['status'], 'error')

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_archive_cache_invalidates_when_source_changes(self):
        z = self.left / 'change.zip'
        with zipfile.ZipFile(z, 'w') as f: f.writestr('one', 'one')
        root = archive.location(str(z))
        self.assertEqual(len(self.service.list_dir(root)['entries']), 1)
        with zipfile.ZipFile(z, 'a') as f: f.writestr('two', 'two')
        self.assertEqual(len(self.service.list_dir(root)['entries']), 2)

    @unittest.skipUnless(os.name == 'posix', 'System libarchive required')
    def test_unsafe_unselected_archive_entry_rejected(self):
        z = self.left / 'bad-selection.zip'
        with zipfile.ZipFile(z, 'w') as f:
            f.writestr('good', 'hello'); f.writestr('../bad', 'escape')
        root = archive.location(str(z))
        with self.assertRaises(ValueError): self.service.list_dir(root)
        state = self.job('copy', [archive.location(str(z), 'good')], self.right)
        self.assertEqual(state['status'], 'error', state)
        self.assertEqual(list(self.right.iterdir()), [])

    def test_virtual_archives_are_read_only(self):
        location = archive.location(str(self.left / 'a.zip'), 'folder/file')
        with self.assertRaises(ValueError): self.service.start('trash', [location])
        with self.assertRaises(ValueError): self.service.start('copy', [str(self.left / 'a')], location)
        with self.assertRaises(ValueError): self.service.mkdir(location, 'new')
        with self.assertRaises(ValueError): self.service.rename(location, 'new')
        with self.assertRaises(ValueError): self.service.open_archive(location)
        with self.assertRaises(ValueError): archive.parse(location + '/../escape')
        self.service.update_settings({'left': location})
        self.assertEqual(self.service.state()['settings']['left'], location)

    def test_empty_trash_reports_success_and_failure(self):
        with patch('fileexplorer.service.trash.empty') as empty:
            empty.return_value = 3
            self.assertEqual(self.job('empty_trash', [])['status'], 'done')
            self.assertEqual(empty.call_args.args[0], str(self.home.resolve()))
            empty.side_effect = ValueError('Cannot empty trash')
            state = self.job('empty_trash', [])
            self.assertEqual(state['status'], 'error')
            self.assertIn('Cannot empty', state['error'])

    @unittest.skipUnless(os.name == 'posix', 'Linux fd-based deletion')
    def test_empty_isolated_trash_home_and_mounts(self):
        mount = self.root / 'disk'; mount.mkdir()
        shared = mount / '.Trash'; shared.mkdir(mode=0o1777); shared.chmod(0o1777)
        outside = self.home / 'keep'; outside.write_text('keep me')
        roots = [self.home / '.local/share/Trash', mount / ('.Trash-' + str(os.getuid())), shared / str(os.getuid())]
        for root in roots:
            files, infos = root / 'files', root / 'info'
            files.mkdir(parents=True); infos.mkdir()
            (files / 'folder').mkdir(); (files / 'folder/item').write_text('remove')
            (files / 'link').symlink_to(outside)
            (infos / 'folder.trashinfo').write_text('metadata')
            (infos / 'link.trashinfo').write_text('metadata')
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.home / '.local/share')}), patch('fileexplorer.trash.mounted_paths', return_value=[mount]):
            state = self.job('empty_trash', [])
        self.assertEqual(state['status'], 'done', state)
        self.assertEqual(outside.read_text(), 'keep me')
        for root in roots:
            self.assertEqual(list((root / 'files').iterdir()), [])
            self.assertEqual(list((root / 'info').iterdir()), [])

    @unittest.skipUnless(os.name == 'posix', 'Linux fd-based deletion')
    def test_empty_trash_rejects_symlink_directory(self):
        root = self.home / '.local/share/Trash'; root.mkdir(parents=True)
        (self.left / 'keep').write_text('keep me')
        (root / 'files').symlink_to(self.left, target_is_directory=True)
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.home / '.local/share')}):
            with self.assertRaises(OSError): trash.empty(self.home, lambda *_: None, mounts=[])
        self.assertEqual((self.left / 'keep').read_text(), 'keep me')

    @unittest.skipUnless(os.name == 'posix', 'Linux fd-based deletion')
    def test_empty_trash_preserves_newly_trashed_metadata(self):
        root = self.home / '.local/share/Trash'; (root / 'files').mkdir(parents=True); (root / 'info').mkdir()
        (root / 'files/old').write_text('old'); (root / 'info/old.trashinfo').write_text('metadata')
        def progress(_, name):
            if name == 'Empty Trash: old':
                (root / 'files/new').write_text('new'); (root / 'info/new.trashinfo').write_text('metadata')
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.home / '.local/share')}):
            self.assertEqual(trash.empty(self.home, progress, mounts=[]), 1)
        self.assertTrue((root / 'files/new').exists())
        self.assertTrue((root / 'info/new.trashinfo').exists())

    def test_discovery_is_bounded_to_local_private_routes(self):
        hosts, nets, limited = discovery.candidates([
            dict(dst='192.168.1.0/24', dev='wlan0', prefsrc='192.168.1.2'),
            dict(dst='10.0.0.0/8', dev='eth0', prefsrc='10.5.6.7'),
            dict(dst='172.17.0.0/16', dev='docker0', prefsrc='172.17.0.1'),
            dict(dst='8.8.8.0/24', dev='eth1', prefsrc='8.8.8.1')])
        self.assertTrue(limited)
        self.assertLessEqual(len(hosts), 512)
        self.assertEqual(nets, ['10.5.6.0/24', '192.168.1.0/24'])
        self.assertNotIn('172.17.0.1', hosts)
        self.assertNotIn('8.8.8.8', hosts)

    def test_discovery_avahi_names(self):
        result = discovery.avahi_servers('=;wlan0;IPv4;My\\032NAS;_smb._tcp;local;nas.local;192.168.1.3;445;\n')
        self.assertEqual(result, {'192.168.1.3': 'My NAS'})


if __name__ == '__main__': unittest.main(verbosity=2)
