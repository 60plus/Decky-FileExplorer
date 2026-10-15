"""Real systemd encryption, legacy migration and an authenticated SMB worker."""
import base64
import json
import multiprocessing
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from fileexplorer import credentials
from fileexplorer.jobs import Jobs, atomic_json, systemd_environment
from fileexplorer.service import Service
from smb_integration import server


def main():
    password = secrets.token_hex(32)
    blob = credentials.seal_password('probe', password)
    assert credentials.unseal_password('probe', blob) == password
    for key, data in [('wrong-name', blob), ('probe', base64.b64encode(base64.b64decode(blob)[:-1] + bytes([base64.b64decode(blob)[-1] ^ 1])).decode())]:
        try: credentials.unseal_password(key, data)
        except credentials.CredentialError: pass
        else: raise AssertionError('Incorrect credential accepted')
    with tempfile.TemporaryDirectory(prefix='fileexplorer-credentials-') as tmp:
        root = Path(tmp); home = root / 'home'; home.mkdir()
        share = root / 'share'; share.mkdir()
        payload = secrets.token_bytes(1024 * 1024)
        (share / 'worker.bin').write_bytes(payload)
        settings = root / 'settings'; settings.mkdir(mode=0o700)
        config = settings / 'settings.json'
        profile = dict(host='127.0.0.1', port=1445, share='TEST', username='fileexplorer-test',
                       password=password, domain='', label='Credential test')
        config.write_text(json.dumps(dict(settings={'left': 'smb://stable-id/'}, connections={'stable-id': profile})))
        config.chmod(0o600)
        process = multiprocessing.Process(target=server, args=(str(share), password)); process.start()
        service = None; jobs = None
        try:
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', 1445), .2): break
                except OSError: time.sleep(.05)
            service = Service(home, settings)
            assert not service.state()['credential_error']
            assert password not in config.read_text() and '"password"' not in config.read_text()
            saved = json.loads(config.read_text())['connections']['stable-id']
            assert credentials.password_for('stable-id', saved) == password
            assert service.config['settings']['left'] == 'smb://stable-id/'
            assert not any(key in json.dumps(service.state()) for key in [password, 'password_credential', saved['password_credential']])
            assert service.list_dir('smb://stable-id/')['entries']
            assert service.shares(dict(host='127.0.0.1', connection_id='stable-id'))
            service.shutdown(); service = Service(home, settings)
            assert service.list_dir('smb://stable-id/')['entries']
            # The child has no in-memory copy of the original password.
            code = "import sys; from fileexplorer.service import Service; s=Service(sys.argv[1],sys.argv[2]); assert s.list_dir('smb://stable-id/')['entries']; s.shutdown(); print('fresh-process-ok')"
            child = subprocess.run([sys.executable, '-c', code, str(home), str(settings)],
                                   env={**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + str(ROOT / 'vendor')},
                                   capture_output=True, timeout=30)
            assert child.returncode == 0 and child.stdout.strip() == b'fresh-process-ok', 'Fresh-process SMB failed'
            for name, remembered in [('saved', True), ('session', False)]:
                destination = home / name; destination.mkdir()
                if remembered: key = 'stable-id'
                else: key = service.connect(dict(profile, remember=False))['id']
                jobs = Jobs(service)
                def check_request(path, value):
                    if Path(path).name == 'request.json':
                        assert password not in json.dumps(value)
                        assert credentials.password_for(key, value['connections'][key]) == password
                    atomic_json(path, value)
                with patch('fileexplorer.jobs.atomic_json', side_effect=check_request):
                    jobs.start('copy', [f'smb://{key}/worker.bin'], str(destination))
                service.shutdown(); service = Service(home, settings); jobs = Jobs(service)
                for _ in range(600):
                    state = jobs.state()
                    if state['status'] != 'running': break
                    time.sleep(.1)
                assert state['status'] == 'done', state
                assert (destination / 'worker.bin').read_bytes() == payload
                assert not (jobs.current_dir() / 'request.json').exists()
                assert [n['milestone'] for n in jobs.notifications(False)] == [25, 50, 75, 100]
            for path in settings.rglob('*'):
                if path.is_file(): assert password.encode() not in path.read_bytes(), str(path)
            service.forget('stable-id')
            assert not json.loads(config.read_text())['connections']
            print(json.dumps(dict(status='passed', protection=credentials.protection(blob), checks=[
                'real encrypted roundtrip', 'wrong name and tamper rejected', 'plaintext migration with IDs and paths preserved',
                'UI omits plaintext and ciphertext', 'SMB browse and list shares after migration', 'fresh process reconnect',
                'saved and session-only encrypted worker requests', 'workers continue after client shutdown',
                'content verified', '25/50/75/100 events', 'no plaintext in durable settings/jobs', 'forget removes ciphertext'])))
        finally:
            if jobs:
                state = jobs.state()
                if state and state['status'] == 'running':
                    subprocess.run(['systemctl', '--user', 'stop', 'fileexplorer-job-' + state['id']], env=systemd_environment(), capture_output=True)
            if service: service.shutdown()
            process.terminate(); process.join(5)


if __name__ == '__main__': main()
