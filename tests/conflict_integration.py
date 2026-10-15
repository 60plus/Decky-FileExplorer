"""Detached local/SMB conflict choices; all data belongs to temporary test folders."""
import json, multiprocessing, os, secrets, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'vendor'), str(ROOT)]
from fileexplorer.service import Service
from fileexplorer.jobs import Jobs, systemd_environment
from fileexplorer.vfs import join
from smb_integration import server


def main():
    with tempfile.TemporaryDirectory(prefix='fileexplorer-conflicts-') as temp:
        root = Path(temp); left = root/'left'; left.mkdir(); right = root/'right'; right.mkdir()
        shared = root/'share'; shared.mkdir()
        service = Service(root, root/'settings'); jobs = Jobs(service); process = None
        owned = []; checks = []
        def wait(job, predicate, timeout=40):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                state = jobs.state(job['id'])
                if predicate(state): return state
                if state['status'] not in ('running', 'queued'): raise AssertionError(state)
                time.sleep(.1)
            raise AssertionError(('Timed out', state))
        def run(action, source, destination, choice):
            job = jobs.start(action, [source], destination); owned.append(job['id'])
            state = wait(job, lambda s: bool(s.get('conflict')))
            before = state['conflict']
            # A fresh client can answer after the original client has gone away.
            observer = Service(root, root/'settings')
            try:
                manager = Jobs(observer)
                events = manager.notifications(False)
                assert sum(e['milestone'] == 'conflict:' + before['id'] for e in events) == 1
                assert manager.notifications(False) == []
                try: manager.resolve_conflict(job['id'], 'outdated-id', choice)
                except ValueError: pass
                else: raise AssertionError('Stale conflict accepted')
                manager.resolve_conflict(job['id'], before['id'], choice, name='Renamed '+Path(source).name if choice == 'rename' else None)
            finally: observer.shutdown()
            result = wait(job, lambda s: s['status'] != 'running')
            assert result['status'] == ('cancelled' if choice == 'cancel' else 'done'), result
            return result
        try:
            for action in ('copy', 'move'):
                for choice in ('backup', 'overwrite', 'cancel', 'rename'):
                    source = left/f'{action}-{choice}-100%.txt'; source.write_bytes(b'new content')
                    target = right/source.name; target.write_bytes(b'old content')
                    run(action, str(source), str(right), choice)
                    assert target.read_bytes() == (b'old content' if choice in ('cancel','rename') else b'new content')
                    if choice == 'rename': assert (right/('Renamed '+source.name)).read_bytes() == b'new content'
                    assert source.exists() == (action == 'copy' or choice == 'cancel')
                    backup = right/(source.name+'.bak')
                    assert backup.exists() == (choice == 'backup')
                    if backup.exists(): assert backup.read_bytes() == b'old content'
                    checks.append('local '+action+' '+choice)
            # Only the conflicting task waits; independent parallel work finishes.
            a = left/'queued-a'; b = left/'queued-b'; a.write_bytes(b'a'); b.write_bytes(b'b')
            (right/a.name).write_bytes(b'old a')
            batch = jobs.submit_copy([str(a), str(b)], str(right), parallel_limit=2)
            owned.extend(j['id'] for j in batch)
            state = wait(batch[0], lambda s: bool(s.get('conflict')))
            assert wait(batch[1], lambda s: s['status'] == 'done')['status'] == 'done'
            jobs.resolve_conflict(batch[0]['id'], state['conflict']['id'], 'backup')
            wait(batch[0], lambda s: s['status'] == 'done')
            checks.append('parallel tasks continue during a conflict')

            for action in ('copy', 'move'):
                for decision in ('resume', 'restart'):
                    source = left/(action+'-'+decision); source.write_text('new')
                    target = right/source.name; target.write_text('old')
                    job = jobs.start(action, [str(source)], str(right)); owned.append(job['id'])
                    state = wait(job, lambda s: bool(s.get('conflict')))
                    if decision == 'resume':
                        try: jobs.resolve_conflict(job['id'], state['conflict']['id'], 'resume')
                        except ValueError as error: assert 'still exists' in str(error)
                        else: raise AssertionError('Resume silently replaced existing data')
                        target.unlink()
                        jobs.resolve_conflict(job['id'], state['conflict']['id'], 'resume')
                        wait(job, lambda s: s['status']=='done')
                        assert target.read_text() == 'new'
                    else:
                        new = jobs.restart_conflict(job['id'], state['conflict']['id']); owned.append(new['id'])
                        done = wait(new, lambda s: s['status']=='done')
                        assert target.read_text() == 'old'
                        assert Path(done['outputs'][0]).read_text() == 'new'
                        assert Path(done['outputs'][0]).parent.name.startswith('FileExplorer retry ')
                    assert source.exists() == (action == 'copy')
                    checks.append(action+' '+decision+' from waiting conflict')

            password = secrets.token_hex(16)
            process = multiprocessing.Process(target=server, args=(str(shared), password)); process.start()
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', 1445), .2): break
                except OSError: time.sleep(.05)
            remote = service.connect(dict(host='127.0.0.1', port=1445, share='TEST', username='fileexplorer-test', password=password, remember=False))['path']
            for action in ('copy', 'move'):
                for choice in ('backup', 'overwrite', 'rename'):
                    source = left/f'smb-{action}-{choice}.txt'; source.write_bytes(b'remote new')
                    target = shared/source.name; target.write_bytes(b'remote old')
                    run(action, str(source), remote, choice)
                    assert target.read_bytes() == (b'remote old' if choice == 'rename' else b'remote new')
                    if choice == 'rename': assert (shared/('Renamed '+source.name)).read_bytes() == b'remote new'
                    assert source.exists() == (action == 'copy')
                    backup = shared/(source.name+'.bak')
                    assert backup.exists() == (choice == 'backup')
                    if backup.exists(): assert backup.read_bytes() == b'remote old'
                    checks.append('SMB '+action+' '+choice)
            # Remote folders are replaced as units, preserving all old contents in .bak.
            folder = left/'Folder'; folder.mkdir(); (folder/'new').write_text('new')
            (shared/'Folder').mkdir(); (shared/'Folder/old-only').write_text('old')
            run('copy', str(folder), remote, 'backup')
            assert sorted(p.name for p in (shared/'Folder').iterdir()) == ['new']
            assert (shared/'Folder.bak/old-only').read_text() == 'old'
            checks.append('SMB folder backup without merging')
            print(json.dumps(dict(status='passed', checks=checks)))
        finally:
            for job_id in owned:
                state = jobs.state(job_id)
                if state and state['status'] == 'running':
                    jobs.cancel(job_id)
                    subprocess.run(['systemctl', '--user', 'stop', 'fileexplorer-job-'+job_id], env=systemd_environment(), capture_output=True)
            service.shutdown()
            if process: process.terminate(); process.join(5)


if __name__ == '__main__': main()
