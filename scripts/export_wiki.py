"""Export the repository manual into an existing wiki checkout; never push it."""
import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path, help='Existing clone of the GitHub wiki')
    parser.add_argument('--repo-url', default='https://github.com/60plus/Decky-FileExplorer')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / 'docs/wiki'
    target = args.checkout.resolve()
    base = args.repo_url.rstrip('/')
    if urlsplit(base).scheme != 'https':
        parser.error('--repo-url must be an HTTPS repository URL')
    if not (target / '.git').exists() or target == root:
        parser.error('Use a separate, existing wiki Git checkout')

    exports = {}
    for page in sorted(source.glob('*.md')):
        def link(match):
            label, url = match.groups()
            if urlsplit(url).scheme or url.startswith('#'):
                return match.group(0)
            path, marker, fragment = url.partition('#')
            resolved = (page.parent / path).resolve()
            if not resolved.is_file():
                raise ValueError(f'{page.name}: missing link target {url}')
            relative = resolved.relative_to(root).as_posix()
            if resolved.parent == source and resolved.suffix == '.md':
                destination = f'{base}/wiki/{resolved.stem}'
            else:
                if label.startswith('!'):
                    repository = urlsplit(base).path.strip('/')
                    destination = f'https://raw.githubusercontent.com/{repository}/main/{relative}'
                else:
                    destination = f'{base}/blob/main/{relative}'
            return f'{label}({destination}{marker}{fragment})'

        # Match the image and its enclosing link separately in [![alt](src)](href).
        exports[page.name] = re.sub(r'(!?\[[^\[\]\n]*\]|\])\(([^)\n]+)\)', link,
                                    page.read_text(encoding='utf-8'))
    # Validate all links before changing the checkout. Unrelated pages are kept.
    for name, content in exports.items():
        (target / name).write_text(content, encoding='utf-8', newline='\n')
    print(f'Exported {len(exports)} Markdown files to {target}. Review, commit and push separately.')


if __name__ == '__main__':
    main()
