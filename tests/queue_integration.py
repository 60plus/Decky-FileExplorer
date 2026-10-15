"""Real detached workers, concurrent transfers and SMB; isolated test files only."""
import hashlib
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'vendor'), str(ROOT)]
from fileexplorer.service import Service
from fileexplorer.jobs import Jobs, systemd_environment
from smb_integration import server


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def signal(job, name):
    subprocess.run(['systemctl', '--user', 'kill', '--signal=' + name, '--kill-whom=all',
                    'fileexplorer-job-' + job['id']], env=systemd_environment(), capture_output=True, check=True)


def main():
    with tempfile.TemporaryDirectory(prefix='fileexplorer-queue-') as tmp:
        root = Path(tmp); destination = root / 'target'; destination.mkdir()
        files = []
        for index in range(10):
            path = root / f'Item {index}.bin'
            with path.open('wb') as stream:
                stream.write(secrets.token_bytes(4096)); stream.truncate(32 * 1024**2)
            files.append(str(path))
        args = dict(home=str(root), settings=str(root / 'settings'), files=files, destination=str(destination))
        # Stop only these test workers while they initialize, so the cap can be
        # inspected even on a fast SSD. Neither worker code nor data is mocked.
        code = '''import json,sys,subprocess
from fileexplorer.service import Service
from fileexplorer.jobs import Jobs,systemd_environment
a=json.loads(sys.argv[1]);s=Service(a['home'],a['settings']);j=Jobs(s);original=j._launch
def launch(state):
 original(state)
 subprocess.run(['systemctl','--user','kill','--signal=SIGSTOP','--kill-whom=all','fileexplorer-job-'+state['id']],env=systemd_environment(),check=True,capture_output=True)
j._launch=launch
print(json.dumps(j.submit_copy(a['files'][:8],a['destination'],parallel_limit=5)))
s.shutdown()
'''
        env = {**os.environ, 'PYTHONPATH': str(ROOT)}
        initial = json.loads(subprocess.check_output([sys.executable, '-c', code, json.dumps(args)], env=env, text=True))
        service = Service(root, root / 'settings'); jobs = Jobs(service)
        process = None
        def finish_all(timeout=120):
            deadline = time.monotonic() + timeout; maximum = 0
            while time.monotonic() < deadline:
                states = jobs.list_jobs(); active = [s for s in states if s['status'] == 'running']
                maximum = max(maximum, len(active)); assert len(active) <= 5, states
                if not any(s['status'] in ('running', 'queued', 'paused') for s in states): return maximum
                time.sleep(.05)
            raise AssertionError('Queue timed out')
        try:
            assert [s['status'] for s in initial] == ['running'] * 5 + ['queued'] * 3
            later = jobs.submit_copy(files[8:], str(destination), 'queue', 2)
            assert all(s['status'] == 'queued' for s in later)
            jobs.cancel(initial[7]['id'])
            assert jobs.state(initial[0]['id'])['status'] == 'running'
            assert jobs.state(initial[7]['id'])['status'] == 'cancelled'
            for state in initial[:5]: signal(state, 'SIGCONT')
            # No queue pumping by this observer: the dispatcher advances the
            # entire queue after the creating client has exited.
            maximum = finish_all()
            for index, source in enumerate(files):
                if index == 7:
                    assert not (destination / Path(source).name).exists(); continue
                assert digest(Path(source)) == digest(destination / Path(source).name)
            assert all(jobs.state(s['id'])['status'] == 'done' for s in initial[:7] + later)
            events = jobs.notifications(False)
            for state in initial[:7] + later:
                assert [e['milestone'] for e in events if e['id'] == state['id']] == [25, 50, 75, 100]
            assert Jobs(service).notifications(False) == []

            password = secrets.token_hex(24)
            process = multiprocessing.Process(target=server, args=(str(root), password)); process.start()
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', 1445), .2): break
                except OSError: time.sleep(.05)
            login = service.connect(dict(host='127.0.0.1', port=1445, share='TEST', username='fileexplorer-test', password=password, remember=False))
            remote_destination = root / 'remote'; remote_destination.mkdir()
            remote = jobs.submit_copy(files[:5], login['path'] + 'remote', parallel_limit=3)
            assert sum(s['status'] == 'running' for s in remote) <= 3
            for state in remote:
                folder = jobs._folder(state['id'])
                for name in ('request.json', 'connections.json'):
                    path = folder / name
                    if path.exists(): assert password not in path.read_text()
            service.shutdown(); service = Service(root, root / 'settings'); jobs = Jobs(service)
            assert login['id'] not in service.profiles(), 'Session login unexpectedly saved'
            finish_all()
            assert all(jobs.state(s['id'])['status'] == 'done' for s in remote)
            for source in files[:5]: assert digest(Path(source)) == digest(remote_destination / Path(source).name)
            assert not list((root / 'settings/jobs').glob('*/connections.json'))
            print(json.dumps(dict(status='passed', maximum_observed=maximum, checks=[
                'five real systemd workers', 'creating client exits', 'detached queue advancement',
                'queued batch waits for earlier tasks', 'cancel one queued item', 'source and output SHA-256',
                'independent once-only 25/50/75/100 notifications', 'three concurrent SMB transfers',
                'encrypted session login survives client reload', 'finished credential snapshots removed'])))
        finally:
            for state in jobs.list_jobs():
                if state['status'] in ('queued', 'paused'): jobs.cancel(state['id'])
                elif state['status'] == 'running':
                    try: signal(state, 'SIGCONT')
                    except subprocess.CalledProcessError: pass
                    jobs.cancel(state['id'])
                    subprocess.run(['systemctl', '--user', 'stop', 'fileexplorer-job-' + state['id']], env=systemd_environment(), capture_output=True)
            service.shutdown()
            if process: process.terminate(); process.join(10)


if __name__ == '__main__': main()
