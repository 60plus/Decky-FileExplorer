"""Give screenshots content-specific filenames and update local documentation links."""
import argparse
import hashlib
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if image URLs need refreshing')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    changes = {}
    for image in sorted((root / 'images/screenshots').glob('*.png')):
        stem = re.sub(r'-[0-9a-f]{12}$', '', image.stem)
        digest = hashlib.sha256(image.read_bytes()).hexdigest()[:12]
        target = image.with_name(f'{stem}-{digest}.png')
        if target != image:
            if target.exists():
                raise ValueError(f'Duplicate screenshot: {target.name}')
            changes[image] = target
    if args.check:
        if changes:
            raise SystemExit('Screenshot filenames need refreshing: ' + ', '.join(p.name for p in changes))
        print('Screenshot filenames match their content hashes.')
        return
    for image, target in changes.items():
        image.rename(target)
    for page in [root / 'README.md', *sorted((root / 'docs').rglob('*.md'))]:
        original = page.read_text(encoding='utf-8')
        updated = original
        for image, target in changes.items():
            # A PC filename can be a suffix of a handheld filename. Match the
            # full basename so each capture keeps its own content hash.
            updated = re.sub(r'(?<![\w.-])' + re.escape(image.name) + r'(?![\w.-])', target.name, updated)
        if updated != original:
            page.write_text(updated, encoding='utf-8', newline='\n')
    print(f'Refreshed {len(changes)} screenshot filenames and matching documentation links.')


if __name__ == '__main__':
    main()
