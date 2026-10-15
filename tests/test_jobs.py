import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fileexplorer.jobs import Jobs, atomic_json, systemd_environment
from fileexplorer.service import Service


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.service = Service(root, root / 'settings')
        self.jobs = Jobs(self.service)
        self.folder = self.jobs.root / ('a' * 32); self.folder.mkdir()
        atomic_json(self.jobs.root / 'current.json', {'id': self.folder.name})
        self.state = dict(id=self.folder.name, kind='copy', label='test', status='done', events=[25, 50, 75, 100], error='', percent=100)
        atomic_json(self.folder / 'state.json', self.state)

    def tearDown(self):
        self.service.shutdown(); self.temp.cleanup()

    def test_notification_thresholds_are_once_only_across_reload(self):
        events = self.jobs.notifications(False)
        self.assertEqual([e['milestone'] for e in events], [25, 50, 75, 100])
        self.assertEqual(Jobs(self.service).notifications(False), [])

    def test_open_explorer_suppresses_seen_thresholds(self):
        self.state['events'] = [25, 50]
        atomic_json(self.folder / 'state.json', self.state)
        self.assertEqual(self.jobs.notifications(True), [])
        self.state['events'] = [25, 50, 75, 100]
        atomic_json(self.folder / 'state.json', self.state)
        self.assertEqual([e['milestone'] for e in self.jobs.notifications(False)], [75, 100])

    def test_failure_is_not_reported_as_done(self):
        self.state.update(status='error', percent=42, events=[25], error='Connection lost')
        atomic_json(self.folder / 'state.json', self.state)
        self.assertEqual([e['milestone'] for e in self.jobs.notifications(False)], [25, 'error'])

    def test_cancel_writes_signal_without_deleting_state(self):
        import time
        self.state.update(status='running', updated=time.time())
        atomic_json(self.folder / 'state.json', self.state)
        self.jobs.cancel()
        self.assertTrue((self.folder / 'cancel').exists())
        self.assertEqual(self.jobs.state()['status'], 'running')

    def test_system_tools_do_not_inherit_decky_bundled_libraries(self):
        with patch.dict(os.environ, {'LD_LIBRARY_PATH': '/tmp/_MEI/lib', 'LD_PRELOAD': '/tmp/_MEI/lib.so',
                                     'PYTHONHOME': '/tmp/_MEI', 'PYTHONPATH': '/tmp/_MEI'}, clear=True), patch('os.getuid', return_value=1000, create=True):
            env = systemd_environment()
            self.assertNotIn('LD_LIBRARY_PATH', env)
            self.assertNotIn('LD_PRELOAD', env)
            self.assertNotIn('PYTHONHOME', env)
            self.assertNotIn('PYTHONPATH', env)
            self.assertEqual(env['DBUS_SESSION_BUS_ADDRESS'], 'unix:path=/run/user/1000/bus')
            os.environ['LD_LIBRARY_PATH_ORIG'] = '/system/original'
            self.assertEqual(systemd_environment()['LD_LIBRARY_PATH'], '/system/original')
            self.assertEqual(os.environ['LD_LIBRARY_PATH'], '/tmp/_MEI/lib')

    def test_retry_refuses_stale_job_or_running_operation(self):
        self.state.update(recoverable=True, status='error')
        atomic_json(self.folder / 'state.json', self.state)
        with self.assertRaisesRegex(ValueError, 'no longer'): self.jobs.retry('b' * 32, 'resume')
        with self.assertRaisesRegex(ValueError, 'Choose'): self.jobs.retry(self.state['id'], 'invalid')
        self.state['status'] = 'running'
        import time
        self.state['updated'] = time.time()
        atomic_json(self.folder / 'state.json', self.state)
        with self.assertRaisesRegex(ValueError, 'no longer'): self.jobs.retry(self.state['id'], 'resume')

    def test_cancel_confirmation_cannot_cancel_a_different_job(self):
        with self.assertRaisesRegex(ValueError, 'finished'): self.jobs.cancel('different-job')
        self.assertFalse((self.folder / 'cancel').exists())

    def test_cancel_persists_explicit_keep_or_discard_choice(self):
        import time
        self.state.update(status='running', updated=time.time())
        atomic_json(self.folder / 'state.json', self.state)
        for keep in (True, False):
            self.jobs.cancel(self.state['id'], keep_partial=keep)
            self.assertEqual(json.loads((self.folder / 'cancel').read_text()), {'keep_partial': keep})
        with self.assertRaises(ValueError): self.jobs.cancel(keep_partial='false')

    def test_stopped_worker_becomes_pending_and_is_kept_during_pruning(self):
        from types import SimpleNamespace
        self.state.update(status='running', updated=0, recoverable=True)
        atomic_json(self.folder / 'state.json', self.state)
        with patch('fileexplorer.jobs.subprocess.run', return_value=SimpleNamespace(stdout='inactive\n')):
            pending = self.jobs.pending()
        self.assertEqual(pending[0]['id'], self.folder.name)
        self.assertEqual(pending[0]['status'], 'error')
        self.assertIn('power loss', pending[0]['error'])
        for number in range(6):
            folder = self.jobs.root / f'{number:032x}'; folder.mkdir()
            atomic_json(folder / 'state.json', dict(id=folder.name, status='done'))
        os.utime(self.folder, (1, 1))
        self.jobs._prune(None)
        self.assertTrue(self.folder.exists())

    @unittest.skipUnless(os.name == 'posix', 'Linux detached workers')
    def test_resume_an_older_checkpoint_after_another_operation(self):
        from types import SimpleNamespace
        root = Path(self.temp.name)
        source = root / 'source'; source.write_text('source')
        destination = root / 'target'; destination.mkdir()
        self.state.update(status='cancelled', recoverable=True)
        atomic_json(self.folder / 'state.json', self.state)
        atomic_json(self.folder / 'plan.json', dict(action='copy', sources=[str(source)], destination=str(destination)))
        (self.folder / 'copy.jsonl').write_bytes(b'')
        other = self.jobs.root / ('b' * 32); other.mkdir()
        atomic_json(other / 'state.json', dict(id=other.name, status='done'))
        atomic_json(self.jobs.root / 'current.json', {'id': other.name})
        with patch('fileexplorer.jobs.subprocess.run', return_value=SimpleNamespace(returncode=0)), patch('fileexplorer.jobs.shutil.copytree'):
            new = self.jobs.retry(self.folder.name, 'resume')
        self.assertEqual(json.loads((self.folder / 'state.json').read_text())['superseded_by'], new['id'])
        self.assertEqual(self.jobs.pending(), [])

    def test_forget_removes_job_scoped_credentials(self):
        atomic_json(self.folder / 'connections.json', {'saved': {'password_credential': 'opaque'}, 'other': {'share': 'public'}})
        self.jobs.forget_connection('saved')
        self.assertEqual(json.loads((self.folder / 'connections.json').read_text()), {'other': {'share': 'public'}})


if __name__ == '__main__': unittest.main()
