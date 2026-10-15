"""Prepare Steam shortcut fields without executing the selected application."""
import os
from pathlib import Path
import shlex
import shutil
import stat

from .vfs import split

WINDOWS = {'.exe', '.com', '.bat', '.cmd'}
SCRIPTS = {'.sh': 'bash', '.bash': 'bash', '.zsh': 'zsh', '.fish': 'fish', '.py': 'python3', '.pl': 'perl', '.rb': 'ruby'}
LAUNCHABLE = WINDOWS | set(SCRIPTS) | {'.appimage', '.run', '.bin'}


def quote_argument(value):
    # Steam stores launch arguments as a command line; reject ambiguous targets.
    if any(c in value for c in ('\x00', '\n', '\r', '"', '`', '$')):
        raise ValueError('Rename the file to remove quotes, backticks, dollar signs or line breaks before adding it to Steam')
    return '"' + value + '"'


def prepare(location, make_executable=False):
    key, path = split(location)
    if key: raise ValueError('Copy this file to a local folder or mount the share before adding it to Steam')
    path = os.path.realpath(path)
    info = os.stat(path)
    if not stat.S_ISREG(info.st_mode): raise ValueError('Select a regular executable or script')
    quote_argument(path)
    with open(path, 'rb') as source: header = source.read(256)
    suffix = Path(path).suffix.lower()
    native = header.startswith(b'\x7fELF') or suffix in ('.appimage', '.run', '.bin')
    if suffix not in LAUNCHABLE and not native and not header.startswith(b'#!'):
        raise ValueError('This file is not a recognized application or script')
    interpreter = None
    arguments = ''
    if suffix in SCRIPTS:
        interpreter = shutil.which(SCRIPTS[suffix])
        if not interpreter: raise ValueError('Required interpreter is not installed: ' + SCRIPTS[suffix])
    if header.startswith(b'#!') and suffix not in WINDOWS:
        parts = shlex.split(header.splitlines()[0][2:].decode('utf-8', errors='replace').strip())
        if parts and parts[0] in ('/usr/bin/env', '/bin/env'):
            parts = parts[1:]
            if parts and parts[0] == '-S': parts = parts[1:]
        if not parts or parts[0].startswith('-') or '=' in parts[0]: raise ValueError('Unsupported script interpreter line')
        interpreter = shutil.which(parts[0])
        if not interpreter: raise ValueError('Required interpreter is not installed: ' + parts[0])
        arguments = ' '.join(quote_argument(arg) for arg in parts[1:])
    needs_execute = not interpreter and suffix not in WINDOWS and not bool(info.st_mode & stat.S_IXUSR)
    if make_executable and needs_execute:
        os.chmod(path, stat.S_IMODE(info.st_mode) | stat.S_IXUSR)
        needs_execute = False
    if interpreter:
        arguments = (arguments + ' ' if arguments else '') + quote_argument(path)
    return dict(location=path, name=Path(path).stem or Path(path).name,
                executable=quote_argument(interpreter or path), directory=quote_argument(str(Path(path).parent)),
                arguments=arguments, windows=suffix in WINDOWS, batch=suffix in ('.bat', '.cmd'), needs_execute=needs_execute)


def game_folder(executable='', start_dir='', install_dir=''):
    """Prefer the real shortcut target folder, then Steam's working/install dir."""
    candidates = []
    if isinstance(executable, str) and executable:
        try:
            parts = shlex.split(executable)
            if parts and os.path.isabs(parts[0]) and os.path.isfile(parts[0]):
                # Script shortcuts target an interpreter; use their working dir.
                if os.path.realpath(parts[0]) not in {os.path.realpath(shutil.which(v) or '/nonexistent') for v in SCRIPTS.values()}:
                    candidates.append(os.path.dirname(parts[0]))
        except ValueError: pass
    for value in (start_dir, install_dir):
        if isinstance(value, str) and value: candidates.append(value.strip('"'))
    for path in candidates:
        if os.path.isabs(path) and os.path.isdir(path): return dict(path=os.path.realpath(path))
    raise ValueError('The game folder is unavailable. Install the game locally or reconnect its drive.')
