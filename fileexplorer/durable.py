"""Flush directory entries after publishing durable job data or copied files."""
import errno
import os


def sync_directory(path):
    if os.name != 'posix': return
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try: os.fsync(fd)
        except OSError as error:
            if error.errno not in (errno.EINVAL, errno.ENOTSUP): raise
    finally: os.close(fd)
