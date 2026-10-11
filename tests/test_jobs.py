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


if __name__ == '__main__': unittest.main()
