import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fileexplorer import credentials as c
from fileexplorer.service import Service
from fileexplorer.jobs import Jobs


def envelope(kind='tpm'):
    header = next(key for key, value in c.FORMATS.items() if value == kind)
    return base64.b64encode(bytes.fromhex(header) + b'unit-test-ciphertext').decode()


class CredentialTests(unittest.TestCase):
    def test_system_key_fallback_and_tpm_formats(self):
        for kind in ('system', 'tpm'):
            blob = envelope(kind)
            with patch.object(c, '_run', side_effect=[blob.encode(), b'private password']):
                self.assertEqual(c.seal_password('one', 'private password'), blob)
            self.assertEqual(c.storage_for({'password_credential': blob}, True), kind)

    def test_null_unscoped_unknown_and_damaged_formats_are_refused(self):
        for blob in ('bad!', '', 'a' * 65537, None, base64.b64encode(bytes(128)).decode(),
                     base64.b64encode(bytes.fromhex('058469daf6f54324800549da0f8ea2fb') + bytes(64)).decode()):
            with patch.object(c, '_run') as run, self.assertRaises(c.CredentialError):
                c.unseal_password('one', blob)
            run.assert_not_called()

    def test_verify_before_accepting_encryption(self):
        with patch.object(c, '_run', side_effect=[envelope().encode(), b'different']), self.assertRaises(c.CredentialError):
            c.seal_password('one', 'secret')
        with patch.object(c, '_run', return_value=b'not an encrypted credential'), self.assertRaises(c.CredentialError):
            c.seal_password('one', 'secret')

    def test_named_pipe_transport_and_errors_do_not_leak(self):
        with patch.object(c, 'systemd_environment', return_value={}), patch.object(c.subprocess, 'run') as run:
            run.return_value = SimpleNamespace(returncode=0, stdout=b'result')
            self.assertEqual(c._run('encrypt', 'profile1', b'secret'), b'result')
            args, kwargs = run.call_args
            self.assertEqual(args[0], ['/usr/bin/systemd-creds', '--user', '--name=fileexplorer-smb-profile1', 'encrypt', '-', '-'])
            self.assertEqual(kwargs['input'], b'secret')
            self.assertNotIn('secret', repr(args) + repr(kwargs['env']))
            for fail in (SimpleNamespace(returncode=1, stdout=b'secret', stderr=b'secret'),
                         subprocess.TimeoutExpired('secret', 20, output=b'secret'), OSError('secret')):
                run.side_effect = fail if isinstance(fail, Exception) else None
                run.return_value = fail
                with self.assertRaises(c.CredentialError) as error: c._run('encrypt', 'profile1', b'secret')
                self.assertNotIn('secret', str(error.exception))
        for key in ('../one', '', 'a' * 65, None):
            with self.assertRaises(c.CredentialError): c.credential_name(key)

    def test_profiles_are_copied_and_empty_guest_password_removed(self):
        source = {'one': {'password': 'secret'}, 'guest': {'password': ''}, 'old': {'password_credential': envelope()}}
        before = copy.deepcopy(source)
        with patch.object(c, 'seal_password', return_value=envelope()) as seal:
            result = c.protect_profiles(source)
        self.assertEqual(source, before)
        self.assertEqual(result['guest'], {})
        self.assertEqual(result['old'], before['old'])
        seal.assert_called_once_with('one', 'secret')
        self.assertNotIn('secret', json.dumps(result))


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = self.root / 'settings'; self.settings.mkdir()
        self.file = self.settings / 'settings.json'
        self.old = {'settings': {'left': 'smb://same-id/folder', 'ui_scale': 80},
                    'connections': {'same-id': {'host': 'server', 'share': 'share', 'label': 'My files',
                                               'username': 'user', 'domain': 'WORKGROUP', 'port': 445, 'password': 'secret'}}}
        self.original = json.dumps(self.old).encode()
        self.file.write_bytes(self.original)
        self.services = []

    def tearDown(self):
        for service in self.services: service.shutdown()
        self.temp.cleanup()

    def service(self):
        service = Service(self.root, self.settings); self.services.append(service); return service

    def test_migration_retains_profile_identity_and_never_returns_ciphertext(self):
        with patch.object(c, 'seal_password', return_value=envelope()): service = self.service()
        disk = json.loads(self.file.read_text())
        self.assertEqual(set(disk['connections']), {'same-id'})
        before = dict(self.old['connections']['same-id']); before.pop('password')
        after = dict(disk['connections']['same-id']); after.pop('password_credential')
        self.assertEqual(before, after)
        self.assertEqual(disk['settings']['left'], self.old['settings']['left'])
        self.assertEqual(service.state()['credential_error'], '')
        self.assertNotIn('secret', self.file.read_text())
        state = json.dumps(service.state())
        self.assertNotIn('secret', state); self.assertNotIn(envelope(), state)
        self.assertEqual(service.state()['connections'][0]['password_storage'], 'tpm')
        with patch.object(c, '_run') as crypto:
            fresh = self.service()
            fresh.list_dir(str(self.root))
        crypto.assert_not_called()  # A local operation does not need SMB credentials.
        if os.name == 'posix': self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(self.settings.glob('.settings-*')))

    def test_failed_migration_keeps_original_and_retries(self):
        with patch.object(c, 'seal_password', side_effect=c.CredentialError(c.SAVE_ERROR)):
            service = self.service()
            self.assertIn('still unencrypted', service.state()['credential_error'])
            self.assertEqual(service.state()['connections'][0]['password_storage'], 'legacy')
            self.assertEqual(self.file.read_bytes(), self.original)
        with patch.object(c, 'seal_password', return_value=envelope('system')):
            service.save()
        self.assertEqual(service.state()['credential_error'], '')
        self.assertEqual(service.state()['connections'][0]['password_storage'], 'system')

    def test_partial_migration_and_disk_failure_never_lose_original(self):
        self.old['connections']['two'] = dict(self.old['connections']['same-id'])
        self.original = json.dumps(self.old).encode(); self.file.write_bytes(self.original)
        with patch.object(c, 'seal_password', side_effect=[envelope(), c.CredentialError(c.SAVE_ERROR)]):
            service = self.service()
        self.assertEqual(self.file.read_bytes(), self.original)
        self.assertIn('password', service.config['connections']['same-id'])
        with patch.object(c, 'seal_password', return_value=envelope()), patch('fileexplorer.service.os.replace', side_effect=OSError()):
            with self.assertRaises(OSError): service.save()
        self.assertEqual(self.file.read_bytes(), self.original)
        self.assertFalse(list(self.settings.glob('.settings-*')))

    def test_unavailable_encryption_connects_session_only_with_warning(self):
        self.file.unlink(); service = self.service()
        with patch('fileexplorer.service.VFS'), patch.object(c, 'seal_password', side_effect=c.CredentialError(c.SAVE_ERROR)):
            result = service.connect(dict(host='server', share='files', password='secret', remember=True))
        state = service.state()
        self.assertFalse(state['connections'][0]['saved'])
        self.assertIn('session only', state['credential_error'])
        self.assertNotIn('secret', json.dumps(state))
        self.assertFalse(self.file.exists())
        service.update_settings({'show_hidden': True})
        self.assertNotIn('secret', self.file.read_text())
        self.assertTrue(service.state()['credential_error'])
        service.forget(result['id'])
        self.assertEqual(service.state()['credential_error'], '')

    @unittest.skipUnless(os.name == 'posix', 'Linux detached workers')
    def test_session_worker_request_is_encrypted_and_missing_store_refuses_job(self):
        self.file.unlink(); service = self.service()
        service.session_connections['session'] = {'host': 'test', 'share': 'test', 'password': 'session-secret'}
        jobs = Jobs(service)
        with patch.object(service, 'validate_job', return_value=['smb://session/file']), \
             patch('fileexplorer.jobs.shutil.copytree'), patch('fileexplorer.jobs.subprocess.run', return_value=SimpleNamespace(returncode=0)), \
             patch.object(c, 'seal_password', return_value=envelope()):
            jobs.start('copy', ['smb://session/file'], str(self.root))
        request = json.loads((jobs.current_dir() / 'request.json').read_text())
        self.assertEqual(request['connections']['session'], {'host': 'test', 'share': 'test', 'password_credential': envelope()})
        self.assertNotIn('session-secret', json.dumps(request))
        self.assertEqual(service.session_connections['session']['password'], 'session-secret')
        state = jobs.state(); state['status'] = 'done'
        from fileexplorer.jobs import atomic_json
        atomic_json(jobs.current_dir() / 'state.json', state)
        with patch.object(service, 'validate_job', return_value=['smb://session/file']), \
             patch('fileexplorer.jobs.shutil.copytree'), patch('fileexplorer.jobs.subprocess.run') as run, \
             patch.object(c, 'seal_password', side_effect=c.CredentialError(c.SAVE_ERROR)):
            with self.assertRaises(c.CredentialError): jobs.start('copy', ['smb://session/file'], str(self.root))
        run.assert_not_called()


if __name__ == '__main__': unittest.main()
