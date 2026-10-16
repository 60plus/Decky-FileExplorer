"""Shutdown regressions shared with the Store edition, with updater routes retained."""
import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]


class PluginRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.settings = self.root / 'settings'
        self.settings.mkdir()

    def test_unload_never_yields_to_the_event_loop(self):
        # Decky's socket reader spins without suspending once the loader closes
        # the RPC socket, so an _unload that awaits anything never resumes.
        decky_stub = SimpleNamespace(DECKY_USER_HOME=str(self.home), DECKY_PLUGIN_SETTINGS_DIR=str(self.settings))
        with patch.dict(sys.modules, {'decky': decky_stub}):
            spec = importlib.util.spec_from_file_location('plugin_main', ROOT / 'main.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin = module.Plugin()

            async def first_step():
                await plugin._main()
                unload = plugin._unload()
                try:
                    unload.send(None)  # A yielding _unload returns the awaited future here.
                except StopIteration:
                    return True
                finally:
                    unload.close()
                return False
            self.assertTrue(asyncio.run(first_step()), '_unload suspended on an awaitable')

    @unittest.skipUnless(os.name == 'posix', 'Decky stops plugins with SIGTERM and a Unix socket')
    def test_unload_completes_after_decky_closes_its_socket(self):
        import select
        import signal
        import socket
        import time
        fixture = ROOT / 'tests' / 'shutdown_fixture.py'
        for legacy, must_exit in ((True, False), (False, True)):
            with self.subTest(unload='await to_thread' if legacy else 'current'):
                marker = self.root / f'unloaded-{int(legacy)}'
                command = [sys.executable, str(fixture), str(self.home), str(self.settings), str(marker)] + (['legacy'] if legacy else [])
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    ready, _, _ = select.select([process.stdout], [], [], 15)
                    path = process.stdout.readline().strip() if ready else ''
                    if not path:
                        process.kill()
                        self.fail('fixture did not start: ' + process.communicate()[1])
                    client = socket.socket(socket.AF_UNIX)
                    client.connect(path)
                    process.send_signal(signal.SIGTERM)
                    time.sleep(0.1)  # Decky closes the socket one loop step after SIGTERM.
                    client.close()
                    # The legacy reader spins and allocates tasks without bound, so keep its window short.
                    try: code = process.wait(timeout=3 if must_exit else 1.5)
                    except subprocess.TimeoutExpired: code = None
                    if code is None:
                        process.kill()
                        process.wait()
                    self.assertEqual(code is not None, must_exit, 'plugin exit after SIGTERM + socket EOF')
                    if must_exit:
                        self.assertEqual(code, 0, process.communicate()[1])
                        self.assertEqual(marker.read_text(), 'unloaded')
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()


if __name__ == '__main__':
    unittest.main()
