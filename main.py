import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
sys.path.insert(0, str(Path(__file__).parent))
import decky
from fileexplorer.service import Service, error_message
from fileexplorer.jobs import Jobs
from fileexplorer.updates import Updates
from fileexplorer import shortcuts


class Plugin:
    async def _main(self):
        self.service = Service(decky.DECKY_USER_HOME, decky.DECKY_PLUGIN_SETTINGS_DIR)
        self.jobs = Jobs(self.service)
        self.updates = Updates(self.service)
        await asyncio.to_thread(self.jobs.ensure_dispatcher)

    async def _unload(self):
        # Decky closes its RPC socket during unload. On current loaders the EOF
        # reader can starve this loop, so yielding here prevents unload returning
        # even after the cleanup thread has finished. This coroutine must finish
        # without yielding. Close local resources synchronously; long-running
        # transfers belong to detached workers.
        if hasattr(self, 'service'): self.service.shutdown()

    async def _migration(self):
        pass

    def state(self):
        result = self.service.state()
        result['job'] = self.jobs.state()
        result['jobs'] = self.jobs.list_jobs()
        return result

    def settings(self, changes):
        self.service.update_settings(changes)
        return self.state()

    def forget(self, key):
        self.service.forget(key)
        self.jobs.forget_connection(key)
        return True

    async def request(self, method, args=None):
        args = args or {}
        try:
            if not hasattr(self, 'service'): await self._main()
            routes = dict(state=self.state, list=self.service.list_dir, settings=self.settings,
                          setup_profiles=self.service.setup_profiles, setup=self.service.setup, claim_splash=self.service.claim_splash,
                          locations=self.service.locations, connect=self.service.connect, forget=self.forget,
                          discover=self.service.discover, shares=self.service.shares, open_archive=self.service.open_archive,
                          mkdir=self.service.mkdir, rename=self.service.rename, preview=self.service.preview,
                          read_text=self.service.read_text, save_text=self.service.save_text, image=self.service.image,
                          read_draft=self.service.drafts.read, save_draft=self.service.drafts.save,
                          discard_draft=self.service.drafts.discard,
                          open_media=self.service.open_media, close_media=self.service.close_media,
                          start=self.jobs.start_operation, job=self.jobs.state, cancel=self.jobs.cancel, notifications=self.jobs.notifications,
                          submit_copy=self.jobs.submit_copy, jobs=self.jobs.list_jobs, resume_queue=self.jobs.resume_queue,
                          resolve_conflict=self.jobs.resolve_conflict,
                          restart_conflict=self.jobs.restart_conflict,
                          retry=self.jobs.retry,
                          interrupted_copies=self.jobs.pending, discard_copy=self.jobs.discard,
                          shortcut_info=shortcuts.prepare, game_folder=shortcuts.game_folder,
                          check_updates=self.updates.check, prepare_update=self.updates.prepare, startup_update=self.updates.startup)
            if method not in routes: raise ValueError('Unknown request')
            return dict(ok=True, data=await asyncio.to_thread(routes[method], **args))
        except Exception as error:
            return dict(ok=False, error=error_message(error))
