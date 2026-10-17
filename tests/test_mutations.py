import unittest
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch

import test_queue as queue_fixtures
from fileexplorer import trash
from fileexplorer.jobs import Jobs, atomic_json


class ConcurrentMutationTests(unittest.TestCase):
    tearDown = queue_fixtures.QueueTests.tearDown
    submit = queue_fixtures.QueueTests.submit
    active = queue_fixtures.QueueTests.active
    finish = queue_fixtures.QueueTests.finish

    def setUp(self):
        queue_fixtures.QueueTests.setUp(self)
        patch('fileexplorer.trash.mounted_paths', return_value=[self.root / 'disk']).start()
        self.service.session_connections['test'] = dict(host='nas', share='data')
        self.remote = [f'smb://test/file-{index}.txt' for index in range(12)]

    def test_unrelated_rename_and_mkdir_work_during_copy(self):
        copied = self.submit(self.files[:1])[0]
        renamed = self.jobs.rename(self.files[1], 'renamed.txt')
        created = self.jobs.mkdir(str(self.root), 'New folder')
        self.assertEqual(Path(renamed).read_text(), '1')
        self.assertTrue(Path(created).is_dir())
        self.assertFalse(Path(self.files[1]).exists())
        self.assertEqual(self.jobs.state(copied['id'])['status'], 'running')

    def test_rename_protects_copy_source_destination_and_parent(self):
        copied = self.submit(self.files[:1])[0]
        for location, name in [(self.files[0], 'other.txt'),
                               (self.files[1], Path(self.files[0]).name),
                               (str(self.destination), 'moved-target')]:
            with self.assertRaisesRegex(ValueError, 'running or queued operation'):
                self.jobs.rename(location, name)
        self.assertTrue(Path(self.files[0]).exists())
        self.finish(copied)
        self.assertTrue(Path(self.jobs.rename(self.files[0], 'finished.txt')).is_file())

    def test_new_folder_inside_copy_source_is_protected(self):
        source = self.root / 'Source'; source.mkdir()
        (source / 'file').write_text('keep')
        self.submit([str(source)])
        with self.assertRaisesRegex(ValueError, 'running or queued operation'):
            self.jobs.mkdir(str(source), 'New folder')
        self.assertFalse((source / 'New folder').exists())

    def test_mutations_protect_queued_and_paused_sources(self):
        items = self.submit(self.files[:2])
        for status in ('queued', 'paused'):
            state = self.jobs.state(items[1]['id']); state['status'] = status
            atomic_json(self.jobs._folder(state['id']) / 'state.json', state)
            with self.assertRaisesRegex(ValueError, 'running or queued operation'):
                self.jobs.rename(self.files[1], 'too-early.txt')

    def test_trash_and_delete_run_beside_copy_but_empty_waits_for_trash(self):
        copied = self.submit(self.files[:1])[0]
        trashed = self.jobs.start_operation('trash', self.files[1:2])
        deleted = self.jobs.start_operation('delete', self.remote[2:3])
        emptied = self.jobs.start_operation('empty_trash', [])
        self.assertEqual(trashed['status'], 'running')
        self.assertEqual(deleted['status'], 'running')
        self.assertEqual(emptied['status'], 'queued')
        self.finish(trashed); self.jobs.pump()
        self.assertEqual(self.jobs.state(emptied['id'])['status'], 'running')
        self.assertEqual(self.jobs.state(copied['id'])['status'], 'running')

    def test_delete_does_not_overtake_an_earlier_queued_copy(self):
        items = self.submit(self.remote[:2])
        deleted = self.jobs.start_operation('delete', self.remote[1:2])
        self.assertEqual(deleted['status'], 'queued')
        self.finish(items[0]); self.jobs.pump()
        self.assertEqual(self.jobs.state(items[1]['id'])['status'], 'running')
        self.assertEqual(self.jobs.state(deleted['id'])['status'], 'queued')
        self.finish(self.jobs.state(items[1]['id'])); self.jobs.pump()
        self.assertEqual(self.jobs.state(deleted['id'])['status'], 'running')

    def test_empty_trash_waits_for_copy_into_a_trash_root(self):
        destination = self.root / '.local/share/Trash/files'
        copied = self.jobs.submit_copy(self.files[:1], str(destination))[0]
        emptied = self.jobs.start_operation('empty_trash', [])
        self.assertEqual(emptied['status'], 'queued')
        self.finish(copied); self.jobs.pump()
        self.assertEqual(self.jobs.state(emptied['id'])['status'], 'running')

    def test_delete_jobs_share_the_five_slot_limit(self):
        self.submit(self.files[:1])
        entries = [self.jobs.start_operation('delete', [path]) for path in self.remote[1:6]]
        self.assertEqual(len(self.active()), 5)
        self.assertEqual(entries[-1]['status'], 'queued')

    def test_trash_reserves_not_yet_created_locations_and_xdg(self):
        mount = self.root / 'disk'
        with patch.dict('os.environ', {'XDG_DATA_HOME': str(self.root / 'custom')}):
            roots = trash.reservation_roots(self.root, [mount])
        import os
        self.assertIn(self.root / 'custom/Trash', roots)
        self.assertIn(self.root / '.local/share/Trash', roots)
        self.assertIn(mount / ('.Trash-' + str(os.getuid())), roots)
        self.assertIn(mount / '.Trash' / str(os.getuid()), roots)

    def test_slow_network_rename_does_not_lock_queue_but_keeps_path_reserved(self):
        entered, release = Event(), Event()
        other = Jobs(self.service)
        def slow_rename(location, name):
            entered.set()
            if not release.wait(5): raise TimeoutError('Test rename was not released')
            return 'smb://test/' + name
        with patch.object(self.service, 'rename', side_effect=slow_rename), ThreadPoolExecutor(2) as pool:
            operation = pool.submit(self.jobs.rename, self.remote[0], 'new.txt')
            try:
                self.assertTrue(entered.wait(2))
                self.assertEqual(pool.submit(other.list_jobs).result(timeout=1), [])
                blocked = other.submit_copy(self.remote[:1], str(self.destination), 'parallel')[0]
                free = other.submit_copy(self.files[1:2], str(self.destination), 'parallel')[0]
                self.assertEqual(blocked['status'], 'queued')
                self.assertEqual(free['status'], 'running')
                with self.assertRaisesRegex(ValueError, 'already being changed'):
                    other.rename(self.remote[0], 'racing.txt')
            finally: release.set()
            self.assertEqual(operation.result(timeout=2), 'smb://test/new.txt')
        other.pump()
        self.assertEqual(other.state(blocked['id'])['status'], 'running')
        self.assertFalse(list(self.jobs.root.glob('mutation-*.json')))

    def test_failed_mutation_releases_its_paths(self):
        with patch.object(self.service, 'rename', side_effect=OSError('Disconnected')):
            with self.assertRaises(OSError): self.jobs.rename(self.files[0], 'new.txt')
        self.assertFalse(list(self.jobs.root.glob('mutation-*.json')))
        self.assertEqual(self.submit(self.files[:1])[0]['status'], 'running')

    def test_unlocked_mutation_file_is_discarded_after_owner_exit(self):
        from fileexplorer.transfer_paths import resources
        lease = self.jobs.root / ('mutation-' + 'a'*32 + '.json')
        lease.write_text(json.dumps(resources('rename', self.files[:1], None, None, {}, self.root)))
        self.assertEqual(self.submit(self.files[:1])[0]['status'], 'running')
        self.assertFalse(lease.exists())

    def test_conflict_choice_respects_an_in_progress_rename(self):
        copied = self.submit(self.files[:1])[0]
        folder = self.jobs._folder(copied['id'])
        atomic_json(folder/'conflict.json', dict(id='choice', target=self.files[0], backup=self.files[0]+'.bak'))
        with self.jobs._mutation('rename', self.files[1:2]):
            with self.assertRaisesRegex(ValueError, 'being changed'):
                self.jobs.resolve_conflict(copied['id'], 'choice', 'rename', Path(self.files[1]).name)
        self.assertFalse((folder/'conflict-response.json').exists())

    def test_waiting_for_paused_source_explains_how_to_proceed(self):
        copied = self.submit(self.files[:1])[0]
        copied['status'] = 'paused'
        atomic_json(self.jobs._folder(copied['id'])/'state.json', copied)
        queued = self.jobs.start_operation('trash', self.files[:1])
        self.assertEqual(queued['status'], 'queued')
        self.assertIn('Resume or cancel', queued['phase'])
