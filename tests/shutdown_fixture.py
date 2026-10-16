"""Regression fixture for the fixed FileExplorer shutdown bug.

The current main.py closes its local resources synchronously in _unload and
passes this shutdown scenario. The optional "legacy" mode deliberately restores
the old, broken implementation so the regression test can prove that it hangs.
The failure described below is the condition the fix protects against, not an
unresolved failure in the current plugin. This file is test-only and is excluded
from the installable ZIP.

Decky 3.2.x stops a plugin by sending SIGTERM and then closing its RPC socket
(plugin.py stop() -> terminate(), then the cancelled response listener calls
close_socket_connection()). The loader's socket reader (localsocket.py
_read_single_line / _listen_for_method_call) returns immediately at EOF without
suspending, so once the socket is closed the plugin's event loop never runs any
other callback again. An _unload that yields to the loop therefore never
resumes and Decky sends SIGKILL after five seconds.

This fixture mirrors that reader and the sandboxed_plugin shutdown sequence
(await _unload -> loop.stop -> sys.exit). It is test-only and never shipped.
Arguments: home settings marker [legacy]. "legacy" restores the pre-fix _unload
that awaited the cleanup in a thread, with a cleanup as slow as the media
server's shutdown poll (0.5 s), to show the hang.
"""
import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[1]


class DeckySocket:
    """Reader semantics copied from decky_loader/localplatform/localsocket.py (v3.2.10)."""

    def __init__(self, path, on_new_message):
        self.path, self.on_new_message, self.active = path, on_new_message, True

    async def setup_server(self):
        self.server = await asyncio.start_unix_server(self._listen_for_method_call, path=self.path, limit=2 ** 20)

    async def _read_single_line(self, reader):
        line = bytearray()
        while self.active:
            try:
                line.extend(await reader.readuntil())
            except asyncio.LimitOverrunError:
                line.extend(await reader.read(reader._limit))
                continue
            except asyncio.IncompleteReadError as err:
                line.extend(err.partial)  # At EOF this returns at once, without suspending.
                break
            else:
                break
        return line.decode('utf-8')

    async def _listen_for_method_call(self, reader, writer):
        while self.active and self.on_new_message:
            line = await self._read_single_line(reader)
            asyncio.create_task(self.on_new_message(line))


def run(home, settings, marker, legacy):
    sys.modules['decky'] = types.SimpleNamespace(DECKY_USER_HOME=home, DECKY_PLUGIN_SETTINGS_DIR=settings)
    sys.path.insert(0, str(ROOT))
    import main as plugin_module
    from fileexplorer.service import Service
    original_shutdown = Service.shutdown

    def slow_shutdown(self):
        time.sleep(0.3)  # Comparable to ThreadingHTTPServer.shutdown() waiting for its poll interval.
        original_shutdown(self)
    Service.shutdown = slow_shutdown
    if legacy:
        async def unload(self):
            if hasattr(self, 'service'): await asyncio.to_thread(self.service.shutdown)
        plugin_module.Plugin._unload = unload

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    plugin = plugin_module.Plugin()

    async def on_new_message(message):
        json.loads(message)

    async def shutdown():  # sandboxed_plugin.SandboxedPlugin.shutdown, reduced to its control flow.
        await plugin._unload()
        Path(marker).write_text('unloaded')
        loop.call_soon_threadsafe(loop.stop)
        sys.exit(0)
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(shutdown()))
    loop.run_until_complete(plugin._main())
    socket = DeckySocket(os.path.join(tempfile.gettempdir(), f'fe-shutdown-{os.getpid()}.sock'), on_new_message)
    loop.run_until_complete(socket.setup_server())
    print(socket.path, flush=True)
    try:
        loop.run_forever()
    except SystemExit:
        pass
    finally:
        loop.close()
        try: os.unlink(socket.path)
        except OSError: pass


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], sys.argv[3], len(sys.argv) > 4 and sys.argv[4] == 'legacy')
