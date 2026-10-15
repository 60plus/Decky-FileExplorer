"""Environment for system tools outside Decky's bundled Python runtime."""
import os


def systemd_environment():
    env = dict(os.environ)
    original = env.pop('LD_LIBRARY_PATH_ORIG', None)
    for key in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    if original: env['LD_LIBRARY_PATH'] = original
    env.update(XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
               DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
    return env
