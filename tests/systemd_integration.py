"""Real systemd user worker acceptance; only temporary test files are changed."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'vendor'), str(ROOT)]
from fileexplorer.service import Service
from fileexplorer.jobs import Jobs, systemd_environment


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''): h.update(data)
    return h.hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix='fileexplorer-systemd-', dir=Path.home()) as tmp:
        root = Path(tmp); home = root / 'home'; home.mkdir()
        destination = home / 'destination'; destination.mkdir()
        source = home / 'large.bin'
        with source.open('wb') as f:
            f.write(b'FileExplorer systemd test\n'); f.truncate(1024**3)
        args = dict(home=str(home), settings=str(root / 'settings'), source=str(source), destination=str(destination))
        # This client starts a worker and exits completely before we inspect progress.
        code = "import json,sys; from fileexplorer.service import Service; from fileexplorer.jobs import Jobs; a=json.loads(sys.argv[1]); s=Service(a['home'],a['settings']); print(json.dumps(Jobs(s).start('copy',[a['source']],a['destination']))); s.shutdown()"
        env = {**os.environ, 'PYTHONPATH': str(ROOT)}
        initial = json.loads(subprocess.check_output([sys.executable, '-c', code, json.dumps(args)], env=env, text=True))
        service = Service(home, root / 'settings'); observer = Jobs(service)
        saw_running = False; maximum_speed = 0; percents = []
        def wait():
            nonlocal saw_running, maximum_speed
            for _ in range(1200):
                state = observer.state()
                if state['status'] != 'running':
                    assert state['status'] == 'done', state
                    return state
                saw_running = True; maximum_speed = max(maximum_speed, state['speed']); percents.append(state['percent'])
                time.sleep(.1)
            raise AssertionError('Worker timeout')
        try:
            state = wait()
            assert saw_running, 'No running state after the client process exited'
            assert digest(source) == digest(destination / source.name)
            assert state['bytes'] == source.stat().st_size and state['total_bytes'] == source.stat().st_size
            assert state['events'] == [25, 50, 75, 100], state
            assert maximum_speed > 0
            assert not (observer.current_dir() / 'request.json').exists()
            notices = observer.notifications(False)
            assert [e['milestone'] for e in notices] == [25, 50, 75, 100]
            assert Jobs(service).notifications(False) == []
            z = home / 'sample.zip'
            with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as out: out.writestr('folder/file.txt', 'archive worker\n')
            observer.start('extract', [str(z)], str(destination)); wait()
            assert (destination / 'sample/folder/file.txt').read_text() == 'archive worker\n'
            print(json.dumps(dict(status='passed', checks=['systemd worker survives client exit', '1 GiB content hash',
                'durable progress', 'nonzero transfer speed', '25/50/75/100 milestones', 'notification acknowledgement survives reload',
                'temporary credential request removed', 'archive extraction worker'], maximum_speed=maximum_speed,
                observed_percentages=sorted(set(percents)))))
        finally:
            state = observer.state()
            if state and state['status'] == 'running':
                observer.cancel()
                subprocess.run(['systemctl', '--user', 'stop', 'fileexplorer-job-' + state['id']], env=systemd_environment(), check=False)
            service.shutdown()


if __name__ == '__main__': main()
