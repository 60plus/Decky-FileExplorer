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
        def run(action, sources, target=None):
            service.start(action, sources, target)
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
            print(json.dumps(dict(status='passed', protocol='SMB2 loopback', bytes=source.stat().st_size,
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(), checks=['authenticated connect', 'upload',
                'download', 'recursive download', 'remote-to-remote copy', 'mkdir', 'rename', 'delete',
                'saved credential reconnect', 'password not returned to UI', 'wrong password rejected',
                'enumerate disk shares', 'selected extraction to SMB', 'browse remote archive', 'selected extraction from SMB',
                'edit SMB text preserving CRLF and whitespace', 'preview SMB image', 'preview image inside SMB archive'])))
        finally:
            service.shutdown()
            process.terminate(); process.join(5)


if __name__ == '__main__': main()
