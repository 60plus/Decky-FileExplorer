"""Empty freedesktop Trash without requiring a desktop GVFS daemon.

Only the current user's trash roots are opened. Directory descriptors and
O_NOFOLLOW keep symlinks out of the traversal, including during deletion.
"""
import os
import re
import shutil
import stat
from pathlib import Path


def mounted_paths():
    result = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = line.split()
        if len(fields) >= 5:
            result.append(Path(re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), fields[4])))
    return result


def reservation_roots(home, mounts=None):
    """Include trash locations that a concurrent move to Trash may create."""
    uid = str(os.getuid())
    data = os.environ.get('XDG_DATA_HOME', '')
    fallback = Path(home) / '.local/share/Trash'
    result = [fallback, Path(data) / 'Trash' if data and os.path.isabs(data) else fallback]
    for mount in mounted_paths() if mounts is None else mounts:
        result.extend((Path(mount) / ('.Trash-' + uid), Path(mount) / '.Trash' / uid))
    return list(dict.fromkeys(result))


def _inspectable(candidate):
    """Whether an optional per-mount trash is worth opening at all.

    Mounts such as /efi and /esp answer even lstat with a permission error, so
    their .Trash-<uid> candidates must drop out during discovery. This is not
    error handling: a trash folder that exists and then refuses deletion, or
    belongs to another user, or turns out to be a symlink, still reports that.
    """
    try: candidate.lstat()
    except (FileNotFoundError, PermissionError): return False
    return True


def roots(home, mounts=None):
    uid = os.getuid()
    data = os.environ.get('XDG_DATA_HOME', '')
    data_home = Path(data) if data and os.path.isabs(data) else Path(home) / '.local/share'
    result = [data_home / 'Trash']
    for mount in mounted_paths() if mounts is None else mounts:
        mount = Path(mount)
        try:
            if not mount.is_dir() or not os.access(mount, os.R_OK | os.X_OK): continue
        except PermissionError: continue
        candidate = mount / ('.Trash-' + str(uid))
        if _inspectable(candidate): result.append(candidate)
        shared = mount / '.Trash'
        try:
            info = shared.lstat()
            if stat.S_ISDIR(info.st_mode) and info.st_mode & stat.S_ISVTX:
                candidate = shared / str(uid)
                if _inspectable(candidate): result.append(candidate)
        except FileNotFoundError: pass
        except PermissionError: pass  # Inaccessible mounts cannot contain accessible trash.
    return list(dict.fromkeys(result))


def _open_directory(path, uid, parent=None):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    if os.fstat(fd).st_uid != uid:
        os.close(fd)
        raise ValueError('Trash directory is not owned by the current user')
    return fd


def empty(home, progress, mounts=None):
    if not shutil.rmtree.avoids_symlink_attacks:
        raise ValueError('Safe Trash deletion requires Linux directory descriptors')
    uid, removed, visited = os.getuid(), 0, set()
    for root in roots(home, mounts):
        try: trash_fd = _open_directory(root, uid)
        except FileNotFoundError: continue
        try:
            info = os.fstat(trash_fd)
            identity = (info.st_dev, info.st_ino)
            if identity in visited: continue
            visited.add(identity)
            for subdir in ('files', 'info'):
                try: folder_fd = _open_directory(subdir, uid, trash_fd)
                except FileNotFoundError: continue
                try:
                    for name in os.listdir(folder_fd):
                        if subdir == 'info':
                            if not name.endswith('.trashinfo'): continue
                            try:
                                check_fd = _open_directory('files', uid, trash_fd)
                            except FileNotFoundError: check_fd = None
                            if check_fd is not None:
                                try:
                                    try:
                                        os.stat(name[:-10], dir_fd=check_fd, follow_symlinks=False)
                                        continue  # A file was trashed while this operation was running.
                                    except FileNotFoundError: pass
                                finally: os.close(check_fd)
                        progress(0, 'Empty Trash: ' + name)
                        try:
                            info = os.stat(name, dir_fd=folder_fd, follow_symlinks=False)
                            if stat.S_ISDIR(info.st_mode): shutil.rmtree(name, dir_fd=folder_fd)
                            else: os.unlink(name, dir_fd=folder_fd)
                            if subdir == 'files': removed += 1
                        except FileNotFoundError: pass
                finally: os.close(folder_fd)
        finally: os.close(trash_fd)
    return removed
