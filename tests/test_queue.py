import json
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fileexplorer.jobs import Jobs, atomic_json
from fileexplorer.service import Service


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.service = Service(self.root, self.root / 'settings')
        self.jobs = Jobs(self.service)
        self.destination = self.root / 'target'; self.destination.mkdir()
        self.files = []
        for index in range(12):
            source = self.root / f'file-{index}.txt'; source.write_text(str(index))
            self.files.append(str(source))
        self.systemd = patch('fileexplorer.jobs.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='active\n')).start()
        patch('fileexplorer.jobs.shutil.copytree').start()

    def tearDown(self):
        patch.stopall(); self.service.shutdown(); self.temp.cleanup()

    def submit(self, files=None, mode='now', limit=1, jobs=None):
        return (jobs or self.jobs).submit_copy(files or self.files, str(self.destination), mode, limit)

    def active(self):
        return [s for s in self.jobs.list_jobs() if s['status'] == 'running']

    def finish(self, state):
        state.update(status='done', updated=time.time(), recoverable=False, events=[25, 50, 75, 100])
        atomic_json(self.jobs._folder(state['id']) / 'state.json', state)

    def test_sequential_batch_advanced_by_new_manager(self):
        created = self.submit(self.files[:3])
        self.assertEqual([s['status'] for s in created], ['running', 'queued', 'queued'])
        self.finish(created[0])
        Jobs(self.service).pump()
        self.assertEqual([s['id'] for s in self.active()], [created[1]['id']])
        self.jobs.cancel(created[2]['id'])
        self.assertEqual(self.jobs.state(created[1]['id'])['status'], 'running')
        self.assertEqual(self.jobs.state(created[2]['id'])['status'], 'cancelled')
        self.assertFalse((self.jobs._folder(created[2]['id']) / 'request.json').exists())

    def test_global_limit_and_batch_limit_across_concurrent_managers(self):
        self.submit(self.files[:6], limit=2)
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(self.submit, self.files[6:9], 'parallel', 5, Jobs(self.service)),
                       pool.submit(self.submit, self.files[9:], 'parallel', 5, Jobs(self.service))]
            for future in futures: future.result()
        active = self.active()
        self.assertEqual(len(active), 5)
        self.assertEqual(sum(s['parallel_limit'] == 2 for s in active), 2)
        self.finish(active[-1]); self.jobs.pump()
        self.assertEqual(len(self.active()), 5)

    def test_queue_waits_for_entire_earlier_batch_but_parallel_can_start(self):
        first = self.submit(self.files[:3], limit=1)
        after = self.submit(self.files[3:5], 'queue', 2)
        parallel = self.submit(self.files[5:6], 'parallel')
        self.assertEqual(len(self.active()), 2)
        self.assertTrue(all(s['status'] == 'queued' for s in after))
        for item in first:
            self.finish(self.jobs.state(item['id'])); self.jobs.pump()
        self.assertTrue(all(self.jobs.state(s['id'])['status'] == 'running' for s in after))
        self.assertEqual(self.jobs.state(parallel[0]['id'])['status'], 'running')

    def test_boot_change_pauses_queue_until_explicit_resume(self):
        items = self.submit(self.files[:3])
        self.finish(items[0])
        with patch.object(Jobs, 'boot_id', return_value='next-boot'):
            Jobs(self.service).pump()
            self.assertFalse(self.active())
            self.assertEqual(self.jobs.state(items[1]['id'])['status'], 'paused')
            self.jobs.resume_queue()
            self.assertEqual(len(self.active()), 1)

    def test_no_parallel_with_non_copy_operation(self):
        first = self.jobs.start('trash', self.files[:1])
        later = self.submit(self.files[1:3], 'queue', 2)
        self.assertEqual(len(self.active()), 1)
        self.finish(first); self.jobs.pump()
        self.assertTrue(all(self.jobs.state(j['id'])['status'] == 'running' for j in later))

    def test_empty_limit_invalid_and_racing_submission_are_rejected(self):
        for limit in (0, 6, True, 1.5):
            with self.assertRaises(ValueError): self.submit(limit=limit)
        with self.assertRaises(ValueError): self.jobs.submit_copy([], str(self.destination))
        self.submit(self.files[:1])
        with self.assertRaisesRegex(ValueError, 'Another transfer'): self.submit(self.files[1:2])
        with self.assertRaisesRegex(ValueError, 'already running'): self.jobs.start('trash', self.files[1:2])

    def test_failed_dispatcher_preserves_waiting_requests_for_manual_retry(self):
        self.systemd.side_effect = lambda cmd, **_: SimpleNamespace(returncode=1 if 'dispatcher.py' in ' '.join(cmd) else 0, stdout='active\n')
        items = self.submit(self.files[:2])
        self.assertEqual(items[0]['status'], 'running')
        self.assertEqual(items[1]['status'], 'paused')
        self.assertTrue((self.jobs._folder(items[1]['id']) / 'request.json').exists())
        self.systemd.side_effect = None
        self.finish(items[0]); self.jobs.resume_queue()
        self.assertEqual(self.jobs.state(items[1]['id'])['status'], 'running')

    def test_each_job_notifies_once_and_old_history_does_not_replay(self):
        items = self.submit(self.files[:2], limit=2)
        for item in items: self.finish(item)
        events = self.jobs.notifications(False)
        self.assertEqual(len(events), 8)
        self.assertEqual(set(e['id'] for e in events), {j['id'] for j in items})
        self.assertEqual(Jobs(self.service).notifications(False), [])
        folder = self.jobs.root / ('a' * 32); folder.mkdir()
        atomic_json(folder / 'state.json', dict(id=folder.name, status='done', kind='copy', label='old', events=[25, 50, 75, 100], error=''))
        self.assertEqual(self.jobs.notifications(False), [])

    def test_runtime_owner_survives_pruning_and_forget_removes_queued_credentials(self):
        items = self.submit(limit=5)
        owner = items[0]['id']
        self.assertTrue(all(s['runtime_owner'] == owner for s in items))
        self.finish(items[0])
        self.jobs._prune(None)
        self.assertTrue(self.jobs._folder(owner).exists())
        folder = self.jobs._folder(items[-1]['id'])
        request = json.loads((folder / 'request.json').read_text())
        request['connections'] = {'test': {'password_credential': 'opaque'}}
        atomic_json(folder / 'request.json', request)
        atomic_json(folder / 'connections.json', request['connections'])
        self.jobs.forget_connection('test')
        self.assertEqual(json.loads((folder / 'request.json').read_text())['connections'], {})
        self.assertEqual(json.loads((folder / 'connections.json').read_text()), {})


if __name__ == '__main__': unittest.main()
