import json
import unittest
import zipfile
from pathlib import Path

import test_queue as queue_fixtures
from fileexplorer import archive, transfer_paths
from fileexplorer.jobs import atomic_json


class MixedTransferTests(unittest.TestCase):
    setUp = queue_fixtures.QueueTests.setUp
    tearDown = queue_fixtures.QueueTests.tearDown
    submit = queue_fixtures.QueueTests.submit
    active = queue_fixtures.QueueTests.active
    finish = queue_fixtures.QueueTests.finish

    def operation(self, action, sources, destination=None, options=None, mode='parallel'):
        return self.jobs.submit_transfer(action, sources, str(destination or self.destination), mode, 5, options)

    def test_mixed_jobs_share_five_slots(self):
        arc = self.root / 'Example.zip'
        with zipfile.ZipFile(arc, 'w') as output: output.writestr('hello.txt', 'hello')
        created = self.submit(self.files[:1])
        created += self.operation('move', self.files[1:2])
        created += self.operation('pack', self.files[2:4], options=dict(format='zip', level=5, name='Packed'))
        created += self.operation('extract', [str(arc)])
        created += self.operation('copy', [archive.location(str(arc), 'hello.txt')])
        self.assertEqual(len(created), 5)
        self.assertEqual(len(self.active()), 5)
        last = self.operation('move', self.files[5:6])[0]
        self.assertEqual(last['status'], 'queued')
        self.finish(created[0]); self.jobs.pump()
        self.assertEqual(self.jobs.state(last['id'])['status'], 'running')
        self.assertEqual(len(self.active()), 5)
        plan = json.loads((self.jobs._folder(created[2]['id']) / 'plan.json').read_text())
        self.assertEqual(plan['sources'], self.files[2:4])
        self.assertEqual(plan['options']['name'], 'Packed.zip')

    def test_move_waits_for_copy_reading_source(self):
        first = self.submit(self.files[:1])[0]
        moved = self.root / 'moved'; moved.mkdir()
        second = self.operation('move', self.files[:1], moved)[0]
        self.assertEqual(second['status'], 'queued')
        self.assertIn('files used', second['phase'])
        self.finish(first); self.jobs.pump()
        self.assertEqual(self.jobs.state(second['id'])['status'], 'running')

    def test_parent_move_waits_for_child_read_and_symlink_alias(self):
        source = self.root / 'Folder'; source.mkdir(); (source/'child.txt').write_text('test')
        alias = self.root / 'Alias'; alias.symlink_to(source, target_is_directory=True)
        first = self.submit([str(alias/'child.txt')])[0]
        second = self.operation('move', [str(source)])[0]
        self.assertEqual(second['status'], 'queued')
        self.finish(first); self.jobs.pump()
        self.assertEqual(self.jobs.state(second['id'])['status'], 'running')

    def test_legacy_active_job_uses_original_plan(self):
        first = self.submit(self.files[:1])[0]
        plan = self.jobs._folder(first['id']) / 'plan.json'
        value = json.loads(plan.read_text()); value.pop('resources'); value.pop('options')
        atomic_json(plan, value)
        second = self.operation('move', self.files[:1])[0]
        self.assertEqual(second['status'], 'queued')
        independent = self.operation('pack', self.files[1:2], options=dict(format='zip', level=0, name='free'))[0]
        self.assertEqual(independent['status'], 'running')

    def test_reader_waits_for_archive_writer(self):
        first = self.operation('pack', self.files[:1], options=dict(format='zip', level=0, name='out'))[0]
        arc = self.destination/'out.zip'
        second = self.operation('extract', [str(arc)], self.root)[0]
        self.assertEqual(second['status'], 'queued')
        self.finish(first); self.jobs.pump()
        self.assertEqual(self.jobs.state(second['id'])['status'], 'running')

    def test_mixed_queue_barrier_and_nontransfer_exclusion(self):
        first = self.submit(self.files[:1])[0]
        second = self.operation('move', self.files[1:2], mode='queue')[0]
        self.assertEqual(second['status'], 'queued')
        self.finish(first); self.jobs.pump()
        self.assertEqual(self.jobs.state(second['id'])['status'], 'running')
        with self.assertRaises(ValueError): self.operation('delete', self.files[2:3])

    def test_smb_aliases_and_case_share_reservations(self):
        profiles = {'one':dict(host='NAS', share='DATA'), 'two':dict(host='nas', share='data')}
        first = transfer_paths.resources('copy', ['smb://one/Folder/file.txt'], str(self.destination), None, profiles, self.root)
        second = transfer_paths.resources('move', ['smb://two/folder'], str(self.root), None, profiles, self.root)
        self.assertTrue(transfer_paths.overlaps(first, second))
        third = transfer_paths.resources('copy', ['smb://two/FOLDER/file.txt'], str(self.root), None, profiles, self.root)
        self.assertFalse(transfer_paths.overlaps(first, third))

    def test_conflict_rename_cannot_replace_an_active_source(self):
        incoming = self.submit(self.files[:1])[0]
        other = self.operation('copy', self.files[1:2])[0]
        folder = self.jobs._folder(incoming['id'])
        conflict = dict(id='choice', target=self.files[0], backup=self.files[0]+'.bak')
        atomic_json(folder/'conflict.json', conflict)
        with self.assertRaisesRegex(ValueError, 'another transfer'):
            self.jobs.resolve_conflict(incoming['id'], 'choice', 'rename', Path(self.files[1]).name)
        self.assertFalse((folder/'conflict-response.json').exists())
        self.finish(other)
        self.jobs.resolve_conflict(incoming['id'], 'choice', 'rename', Path(self.files[1]).name)
        self.assertTrue((folder/'conflict-response.json').exists())

