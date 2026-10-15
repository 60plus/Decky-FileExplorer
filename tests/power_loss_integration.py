"""Abrupt worker/client death, not a physical battery or filesystem power-cut test."""
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
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from fileexplorer.service import Service
from fileexplorer.jobs import Jobs, systemd_environment
from smb_integration import server


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix='fileexplorer-power-') as tmp:
        root = Path(tmp); home = root / 'home'; home.mkdir()
        settings = root / 'settings'
        source = home / 'large.bin'
        with source.open('wb') as output:
            output.write(secrets.token_bytes(4096)); output.truncate(1024**3)
        expected = digest(source)
        small = home / 'finished.txt'; small.write_text('Completed copies stay')
        service = Service(home, settings); jobs = Jobs(service)
        process = None
        def wait(partial=False, timeout=120):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                state = jobs.state()
                if partial and state['status'] == 'running' and state['bytes'] > 1024 * 1024: return state
                if not partial and state['status'] != 'running': return state
                if partial and state['status'] != 'running': raise AssertionError('Copy finished before interruption')
                time.sleep(.025)
            raise AssertionError('Operation timed out')
        def kill_worker():
            state = wait(partial=True)
            subprocess.run(['systemctl', '--user', 'kill', '--signal=SIGKILL', '--kill-whom=all',
                            'fileexplorer-job-' + state['id']], env=systemd_environment(), check=True, capture_output=True)
            return wait(timeout=25)
        try:
            kept = home / 'kept'; kept.mkdir()
            first = jobs.start('copy', [str(small), str(source)], str(kept)); wait(partial=True)
            jobs.cancel(first['id'], keep_partial=True)
            stopped = wait(); assert stopped['status'] == 'cancelled' and stopped['recoverable'], stopped
            notices = jobs.notifications()
            assert any(n['milestone'] == 'cancelled' and not n['recoverable'] for n in notices), notices
            assert list(kept.glob('.fileexplorer-*.partial'))
            # Another operation must not erase the retained recovery offer.
            other = home / 'other'; other.mkdir()
            jobs.start('copy', [str(small)], str(other)); assert wait()['status'] == 'done'
            service.shutdown(); service = Service(home, settings); jobs = Jobs(service)
            assert first['id'] in [state['id'] for state in jobs.pending()]
            jobs.retry(first['id'], 'resume'); assert wait()['status'] == 'done'
            assert digest(kept / source.name) == expected
            assert not jobs.pending()

            removed = home / 'removed'; removed.mkdir()
            second = jobs.start('copy', [str(small), str(source)], str(removed)); wait(partial=True)
            jobs.cancel(second['id'], keep_partial=False)
            stopped = wait()
            assert stopped['status'] == 'cancelled' and stopped['partial_removed'] and not stopped['recoverable'], stopped
            assert not list(removed.glob('.fileexplorer-*.partial'))
            assert (removed / small.name).read_bytes() == small.read_bytes()

            killed = home / 'killed'; killed.mkdir()
            third = jobs.start('copy', [str(small), str(source)], str(killed))
            stopped = kill_worker(); assert stopped['status'] == 'error' and stopped['recoverable'], stopped
            service.shutdown(); service = Service(home, settings); jobs = Jobs(service)
            assert third['id'] in [state['id'] for state in jobs.pending()]
            jobs.retry(third['id'], 'resume'); assert wait()['status'] == 'done'
            assert digest(killed / source.name) == expected

            # A session-only SMB login must survive in the encrypted job scope.
            password = secrets.token_hex(24)
            process = multiprocessing.Process(target=server, args=(str(home), password)); process.start()
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', 1445), .2): break
                except OSError: time.sleep(.05)
            login = service.connect(dict(host='127.0.0.1', port=1445, share='TEST', username='fileexplorer-test', password=password, remember=False))
            remote_target = home / 'smb-killed'; remote_target.mkdir()
            remote = jobs.start('copy', [login['path'] + source.name], str(remote_target))
            stopped = kill_worker(); assert stopped['status'] == 'error' and stopped['recoverable'], stopped
            assert password not in (jobs.current_dir() / 'connections.json').read_text()
            service.shutdown(); service = Service(home, settings); jobs = Jobs(service)
            assert login['id'] not in service.profiles()
            jobs.retry(remote['id'], 'resume'); assert wait()['status'] == 'done'
            assert digest(remote_target / source.name) == expected
            assert not list(settings.glob('jobs/*/connections.json'))

            # Simulate a dead editor process after the last draft acknowledgement.
            document = home / 'editing.json'; original = b'{\r\n\t"value": 1\r\n}\r\n'; document.write_bytes(original)
            child_code = "import sys,time; from fileexplorer.service import Service; s=Service(sys.argv[1],sys.argv[2]); p=sys.argv[3]; f=s.read_text(p); s.drafts.save(p,'{\\n\\t\"value\": unfinished',f['revision'],f['encoding'],{'anchor':3,'head':3}); print('saved',flush=True); time.sleep(60)"
            child = subprocess.Popen([sys.executable, '-c', child_code, str(home), str(settings), str(document)], stdout=subprocess.PIPE,
                                     env={**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + str(ROOT / 'vendor')})
            try:
                assert child.stdout.readline().strip() == b'saved'
                child.kill(); child.wait(5)
            finally:
                if child.poll() is None: child.kill(); child.wait(5)
            service.shutdown(); service = Service(home, settings); jobs = Jobs(service)
            assert service.drafts.read(str(document))['text'] == '{\n\t"value": unfinished'
            assert document.read_bytes() == original
            assert digest(source) == expected
            print(json.dumps(dict(status='passed', checks=['keep cancellation and later resume after another job',
                'discard removes staging only', 'SIGKILL worker then fresh client recovery', 'local source and destination hashes',
                'SMB session login survives worker/client death as encrypted job credential', 'SMB resumed content hash',
                'finished jobs remove their credential snapshots', 'killed editor client leaves acknowledged draft',
                'incomplete JSON draft leaves original bytes untouched'])))
        finally:
            state = jobs.state()
            if state and state['status'] == 'running':
                subprocess.run(['systemctl', '--user', 'stop', 'fileexplorer-job-' + state['id']], env=systemd_environment(), capture_output=True)
            service.shutdown()
            if process: process.terminate(); process.join(5)


if __name__ == '__main__': main()
