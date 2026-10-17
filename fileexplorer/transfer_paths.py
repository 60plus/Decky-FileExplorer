"""Read/write reservations for independent background transfers."""
from pathlib import Path

from . import archive, moving, trash
from .vfs import VFS, join, split


TRANSFERS = frozenset(('copy', 'move', 'pack', 'extract'))
OPERATIONS = TRANSFERS | {'trash', 'delete', 'empty_trash'}


def resources(action, sources, destination, options, profiles, home):
    fs = VFS(profiles)
    result = []

    def reserve(location, write):
        scope, path = moving.identity(fs, location)
        result.append(dict(scope=scope, path=path.rstrip('/') or '/', write=write))

    try:
        for source in sources:
            virtual = archive.is_location(source)
            physical, member = archive.parse(source) if virtual else (source, '')
            reserve(physical, action in ('move', 'trash', 'delete', 'rename', 'mkdir'))
            if action in ('copy', 'move'):
                reserve(join(destination, Path(member if virtual else split(source)[1]).name), True)
            elif action == 'extract':
                reserve(join(destination, archive.extraction_name(source)), True)
        if action == 'pack':
            reserve(join(destination, options['name']), True)
        if action in ('trash', 'empty_trash'):
            # Serialize trash publication and emptying even before its folders exist.
            result.append(dict(scope='fileexplorer-trash', path='/', write=True))
            for path in trash.reservation_roots(home): reserve(str(path), True)
        return result
    finally:
        fs.close()


def overlaps(first, second):
    for a in first:
        for b in second:
            # JSON turns SMB scope tuples into lists.
            scope_a = tuple(a['scope']) if isinstance(a['scope'], (tuple, list)) else a['scope']
            scope_b = tuple(b['scope']) if isinstance(b['scope'], (tuple, list)) else b['scope']
            if scope_a != scope_b or not (a['write'] or b['write']):
                continue
            ap, bp = a['path'], b['path']
            if ap == bp or ap.startswith(bp.rstrip('/') + '/') or bp.startswith(ap.rstrip('/') + '/'):
                return True
    return False
