"""Optional real SMB2 roundtrip against an isolated loopback Impacket server.

Run on Linux with impacket installed in a test virtualenv. No external share is
touched and the server listens only on 127.0.0.1:1445 during the test.
"""
import hashlib
import base64
import json
import multiprocessing
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import uuid
import zipfile

ROOT = Path(os.environ.get('FILEEXPLORER_SOURCE', Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from fileexplorer.service import Service
from fileexplorer.vfs import VFS, join
from fileexplorer import archive


def server(root, password):
    from impacket.smbserver import SimpleSMBServer
    from impacket.ntlm import compute_lmhash, compute_nthash
    import logging
    logging.disable(logging.CRITICAL)
    smb = SimpleSMBServer(listenAddress='127.0.0.1', listenPort=1445)
    smb.addShare('TEST', root, readOnly='no')
    smb.setSMB2Support(True)
    smb.addCredential('fileexplorer-test', 0, compute_lmhash(password), compute_nthash(password))
    smb.start()


def main():
    with tempfile.TemporaryDirectory(prefix='fileexplorer-smb-') as tmp:
        root = Path(tmp); shared = root / 'share'; shared.mkdir()
        home = root / 'home'; home.mkdir()
        destination = home / 'destination'; destination.mkdir()
        (shared / 'nested').mkdir()
        (shared / 'nested' / 'hello.txt').write_text('SMB directory content')
        source = home / 'Żółw #100%.bin'
        source.write_bytes(bytes(range(256)) * 16384)
        password = uuid.uuid4().hex
        process = multiprocessing.Process(target=server, args=(str(shared), password))
        process.start()
        service = Service(home, root / 'settings')
        def run(action, sources, target=None, options=None):
            service.start(action, sources, target, options)
            for _ in range(1200):
                state = service.job_state()
                if state['status'] != 'running':
                    assert state['status'] == 'done', state
                    return state
                time.sleep(.025)
            raise AssertionError('SMB job timed out')
        try:
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', 1445), .2): break
                except OSError: time.sleep(.05)
            result = service.connect(dict(host='127.0.0.1', port=1445, share='TEST', username='fileexplorer-test', password=password, remember=True))
            remote = result['path']
            # Real SMB range reads and interrupted uploads/downloads, isolated
            # from the user's shares and credentials.
            import urllib.request
            from fileexplorer.copy_resume import CopyResume
            media_bytes = bytes(range(256)) * 8192
            (shared / 'sample.wav').write_bytes(media_bytes)
            stream = service.open_media(join(remote, 'sample.wav'))
            try:
                with urllib.request.urlopen(urllib.request.Request(stream['url'], headers={'Range': 'bytes=1048576-1048831'})) as response:
                    assert response.status == 206 and response.read() == bytes(range(256))
            finally: service.close_media(stream['token'])
            local_media = home / 'resume.bin'; local_media.write_bytes(media_bytes)
            fs_resume = VFS(service.profiles())
            try:
                for number, source_path, destination_path in [
                    (1, str(local_media), join(remote, 'upload-resume')),
                    (2, join(remote, 'sample.wav'), str(home / 'download-resume')),
                    (3, join(remote, 'sample.wav'), join(remote, 'remote-resume')),
                ]:
                    fs_resume.mkdir(destination_path)
                    checkpoint = root / f'copy-{number}.jsonl'
                    def interrupt(n, _):
                        if n: raise OSError('Simulated connection loss after a real SMB write')
                    try: CopyResume(checkpoint, interrupt).copy(fs_resume, source_path, destination_path)
                    except OSError: pass
                    else: raise AssertionError('Copy did not interrupt')
                    output = CopyResume(checkpoint, lambda *_: None).copy(fs_resume, source_path, destination_path)
                    import io
                    check = io.BytesIO(); fs_resume.read_to(output, check, lambda *_: None)
                    assert check.getvalue() == media_bytes
                    discard_to = destination_path + '-discard'; fs_resume.mkdir(discard_to)
                    discard_journal = root / f'discard-{number}.jsonl'
                    try: CopyResume(discard_journal, interrupt).copy(fs_resume, source_path, discard_to)
                    except OSError: pass
                    else: raise AssertionError('Copy did not interrupt')
                    partial = CopyResume(discard_journal, lambda *_: None)
                    stages = [record['stage'] for record in partial.records.values()]
                    partial.discard(fs_resume, [source_path], discard_to)
                    assert not any(fs_resume.exists(stage) for stage in stages)
                    assert fs_resume.exists(source_path) and fs_resume.exists(output)
            finally: fs_resume.close()
            image = (Path(__file__).parent / 'fixtures/images/sample.png').read_bytes()
            (shared / 'picture.png').write_bytes(image)
            preview = service.image(join(remote, 'picture.png'))
            assert base64.b64decode(preview['data'].split(',', 1)[1]) == image
            with zipfile.ZipFile(shared / 'pictures.zip', 'w') as z: z.writestr('nested/picture.png', image)
            preview = service.image(archive.location(join(remote, 'pictures.zip'), 'nested/picture.png'))
            assert base64.b64decode(preview['data'].split(',', 1)[1]) == image
            assert not list(service.settings_dir.glob('.fileexplorer-image-*'))
            assert not list(service.settings_dir.glob('.fileexplorer-read-*'))
            shares = service.shares(dict(host='127.0.0.1', port=1445, username='fileexplorer-test', password=password))
            assert 'TEST' in [s['name'] for s in shares], shares
            (shared / 'settings.cfg').write_bytes(b'\tvalue=1  \r\n\r\nlast=true')
            edit = service.read_text(join(remote, 'settings.cfg'))
            service.save_text(join(remote, 'settings.cfg'), edit['text'].replace('value=1', 'value=2'), edit['revision'], edit['encoding'])
            assert (shared / 'settings.cfg').read_bytes() == b'\tvalue=2  \r\n\r\nlast=true'
            assert not list(shared.glob('.fileexplorer-edit-*')) and not list(shared.glob('.fileexplorer-backup-*'))
            z = home / 'local.zip'
            with zipfile.ZipFile(z, 'w') as f:
                f.writestr('selected/file.txt', 'selected archive content')
                f.writestr('omit.txt', 'not selected')
            run('copy', [archive.location(str(z), 'selected')], remote)
            assert (shared / 'selected/file.txt').read_text() == 'selected archive content'
            assert not (shared / 'omit.txt').exists()
            run('copy', [str(z)], remote)
            virtual = archive.location(join(remote, 'local.zip'))
            assert service.list_dir(virtual)['archive']
            run('copy', [archive.location(join(remote, 'local.zip'), 'selected/file.txt')], str(destination))
            assert (destination / 'file.txt').read_text() == 'selected archive content'
            run('copy', [str(source)], remote)
            uploaded = shared / source.name
            assert uploaded.read_bytes() == source.read_bytes()
            run('copy', [join(remote, source.name)], str(destination))
            assert (destination / source.name).read_bytes() == source.read_bytes()
            run('copy', [join(remote, 'nested')], str(destination))
            assert (destination / 'nested/hello.txt').read_text() == 'SMB directory content'
            # Remote directory creation, rename, and remote-to-remote copy.
            newfolder = service.mkdir(remote, 'remote-copy')
            run('copy', [join(remote, source.name)], newfolder)
            renamed = service.rename(join(newfolder, source.name), 'renamed.bin')
            assert (shared / 'remote-copy/renamed.bin').read_bytes() == source.read_bytes()
            run('delete', [renamed])
            assert not (shared / 'remote-copy/renamed.bin').exists()
            restored = Service(home, root / 'settings')
            try:
                assert len(restored.list_dir(remote)['entries']) >= 3
                assert password not in json.dumps(restored.state())
            finally: restored.shutdown()
            try:
                service.connect(dict(host='127.0.0.1', port=1445, share='TEST', username='fileexplorer-test', password='wrong'))
            except Exception: pass
            else: raise AssertionError('Wrong password accepted')
            # Move only dedicated fixtures; a verified destination must exist
            # before deleting a cross-filesystem source.
            move_data = b'Move verification\x00\xff' * 120000
            moving = home / 'move-local.bin'; moving.write_bytes(move_data)
            run('move', [str(moving)], remote)
            assert not moving.exists() and (shared / moving.name).read_bytes() == move_data
            run('move', [join(remote, moving.name)], str(destination))
            assert not (shared / moving.name).exists() and (destination / moving.name).read_bytes() == move_data
            (shared / 'move-native.bin').write_bytes(move_data)
            run('move', [join(remote, 'move-native.bin')], newfolder)
            assert not (shared / 'move-native.bin').exists() and (shared / 'remote-copy/move-native.bin').read_bytes() == move_data
            # A separately added login has its own credential name and ID.
            alias = service.connect(dict(host='127.0.0.1', port=1445, share='TEST', username='fileexplorer-test',
                                         password=password, remember=False))['path']
            run('move', [join(newfolder, 'move-native.bin')], alias)
            assert not (shared / 'remote-copy/move-native.bin').exists() and (shared / 'move-native.bin').read_bytes() == move_data
            for number, selected, output in [
                (1, [str(destination / moving.name)], remote),
                (2, [join(remote, 'move-native.bin')], str(destination)),
                (3, [join(remote, 'move-native.bin')], newfolder),
            ]:
                result = run('pack', selected, output, dict(format='zip', level=5, name='packed-' + str(number)))
                fs = VFS(service.profiles())
                try:
                    with tempfile.TemporaryFile() as file:
                        fs.read_to(result['outputs'][0], file, lambda *_: None); file.seek(0)
                        with zipfile.ZipFile(file) as archive_file:
                            assert archive_file.read(archive_file.namelist()[0]) == move_data
                finally: fs.close()
            print(json.dumps(dict(status='passed', protocol='SMB2 loopback', bytes=source.stat().st_size,
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(), checks=['authenticated connect', 'upload',
                'download', 'recursive download', 'remote-to-remote copy', 'mkdir', 'rename', 'delete',
                'saved credential reconnect', 'password not returned to UI', 'wrong password rejected',
                'enumerate disk shares', 'selected extraction to SMB', 'browse remote archive', 'selected extraction from SMB',
                'edit SMB text preserving CRLF and whitespace', 'preview SMB image', 'preview image inside SMB archive',
                'ranged SMB media stream', 'resume local-to-SMB', 'resume SMB-to-local', 'resume SMB-to-SMB',
                'discard local-to-SMB staging', 'discard SMB-to-local staging', 'discard SMB-to-SMB staging',
                'verified local-to-SMB move', 'verified SMB-to-local move', 'SMB rename move', 'verified cross-profile SMB move',
                'pack local-to-SMB', 'pack SMB-to-local', 'pack SMB-to-SMB'])))
        finally:
            service.shutdown()
            process.terminate(); process.join(5)


if __name__ == '__main__': main()
