import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
sys.path.insert(0, str(Path(__file__).parent))
import decky
from fileexplorer.service import Service, error_message
from fileexplorer.jobs import Jobs
from fileexplorer.updates import Updates


class Plugin:
    async def _main(self):
        self.service = Service(decky.DECKY_USER_HOME, decky.DECKY_PLUGIN_SETTINGS_DIR)
        self.jobs = Jobs(self.service)
        self.updates = Updates(self.service)

    async def _unload(self):
        if hasattr(self, 'service'): await asyncio.to_thread(self.service.shutdown)

    async def _migration(self):
        pass

    def state(self):
        result = self.service.state()
        result['job'] = self.jobs.state()
        return result

    def settings(self, changes):
        self.service.update_settings(changes)
        return self.state()

    async def request(self, method, args=None):
        args = args or {}
        try:
            if not hasattr(self, 'service'): await self._main()
            routes = dict(state=self.state, list=self.service.list_dir, settings=self.settings,
                          locations=self.service.locations, connect=self.service.connect, forget=self.service.forget,
                          discover=self.service.discover, shares=self.service.shares, open_archive=self.service.open_archive,
                          mkdir=self.service.mkdir, rename=self.service.rename, preview=self.service.preview,
                          read_text=self.service.read_text, save_text=self.service.save_text, image=self.service.image,
                          open_media=self.service.open_media, close_media=self.service.close_media,
                          start=self.jobs.start, job=self.jobs.state, cancel=self.jobs.cancel, notifications=self.jobs.notifications,
                          retry=self.jobs.retry,
                          check_updates=self.updates.check, prepare_update=self.updates.prepare, startup_update=self.updates.startup)
            if method not in routes: raise ValueError('Unknown request')
            return dict(ok=True, data=await asyncio.to_thread(routes[method], **args))
        except Exception as error:
            return dict(ok=False, error=error_message(error))
