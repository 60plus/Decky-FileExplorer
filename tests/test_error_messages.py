"""User-facing connection failures must preserve local errors and copy recovery."""
import errno
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from fileexplorer.copy_resume import CopyResume
from fileexplorer.service import Service, error_message


class ErrorMessageTests(unittest.TestCase):
    def test_socket_failures_hide_raw_details_without_promising_resume(self):
        for error in (ConnectionResetError(errno.ECONNRESET, 'private detail'),
                      ConnectionAbortedError(errno.ECONNABORTED, 'private detail'),
                      ConnectionRefusedError(errno.ECONNREFUSED, 'private detail'),
                      BrokenPipeError(errno.EPIPE, 'private detail'),
                      TimeoutError('private detail'), socket.timeout('private detail'),
                      OSError(errno.ECONNRESET, 'private detail'),
                      OSError(errno.ETIMEDOUT, 'private detail')):
            with self.subTest(error=type(error).__name__):
                message = error_message(error)
                self.assertIn('Check the network and server', message)
                self.assertNotIn('private detail', message)
                self.assertNotIn('Errno', message)
                self.assertNotIn('Resume', message)  # A failed listing has no transfer to resume.

    def test_local_errors_remain_distinct(self):
        self.assertEqual(error_message(PermissionError(errno.EACCES, 'private detail')),
                         'Permission denied. FileExplorer runs as your Steam user.')
        for error in (OSError(errno.ENOSPC, 'No space left on device'),
                      OSError(errno.EROFS, 'Read-only file system'),
                      OSError(errno.EIO, 'Input/output error'),
                      FileNotFoundError(errno.ENOENT, 'No such file'),
                      FileExistsError('Destination already exists'),
                      ValueError('Invalid JSON: timed out is not a quoted string')):
            with self.subTest(error=error):
                self.assertEqual(error_message(error), str(error))

    def test_pysmb_protocol_errors_stay_redacted(self):
        from smb.base import SMBTimeout, NotConnectedError, NotReadyError
        for kind in (SMBTimeout, NotConnectedError, NotReadyError):
            with self.subTest(kind=kind.__name__):
                self.assertEqual(error_message(kind('private protocol dump')),
                                 'SMB operation failed. Check the connection, permissions and credentials.')

    def test_other_errors_keep_bounded_fallback(self):
        self.assertEqual(error_message(RuntimeError()), 'RuntimeError')
        self.assertEqual(error_message(ValueError('x' * 600)), 'x' * 500)

    def test_interrupted_copy_reports_connection_error_and_resumes_same_bytes(self):
        for kind in (ConnectionResetError, TimeoutError):
            with self.subTest(kind=kind.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                home = root / 'home'; home.mkdir()
                source = home / 'source.bin'
                payload = bytes(range(256)) * 12000
                source.write_bytes(payload)
                target = home / 'target'; target.mkdir()
                service = Service(home, root / 'settings')
                journal = root / 'copy.jsonl'
                copied = 0

                def interrupt(size, path):
                    nonlocal copied
                    service.progress(size, path)
                    copied += size
                    if copied >= 1024 * 1024:
                        raise kind('private connection detail')

                def transfer():
                    service.start('copy', [str(source)], str(target))
                    end = time.monotonic() + 10
                    while time.monotonic() < end:
                        state = service.job_state()
                        if state['status'] != 'running': return state
                        time.sleep(.01)
                    self.fail('copy did not finish')

                try:
                    service.copy_resume = CopyResume(journal, interrupt)
                    failed = transfer()
                    self.assertEqual(failed['status'], 'error')
                    self.assertIn('Check the network and server', failed['error'])
                    self.assertNotIn('private connection detail', failed['error'])
                    self.assertFalse((target / source.name).exists())
                    service.copy_resume = CopyResume(journal, service.progress)
                    record = service.copy_resume.records[str(source)]
                    self.assertEqual(Path(record['stage']).stat().st_size, 1024 * 1024)
                    self.assertEqual(transfer()['status'], 'done')
                    self.assertEqual((target / source.name).read_bytes(), payload)
                    self.assertEqual(source.read_bytes(), payload)
                finally:
                    service.shutdown()


if __name__ == '__main__':
    unittest.main()
