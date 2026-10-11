"""Create a Decky install ZIP with all runtime dependencies included."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
version = json.loads((root / 'package.json').read_text())['version']
out = root / 'out'
out.mkdir(exist_ok=True)
artifact = out / f'FileExplorer-{version}.zip'
files = [root / p for p in ('main.py', 'plugin.json', 'package.json', 'LICENSE')]
for folder in ('dist', 'fileexplorer', 'vendor'):
    files.extend(p for p in (root / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
if not (root / 'dist/index.js').exists(): raise SystemExit('Build the frontend first')
if not (root / 'vendor/smb/SMBConnection.py').exists(): raise SystemExit('Install requirements into vendor first')
with zipfile.ZipFile(artifact, 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(files): archive.write(file, 'FileExplorer/' + file.relative_to(root).as_posix())
digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
(out / (artifact.name + '.sha256')).write_text(digest + '  ' + artifact.name + '\n')
print(json.dumps(dict(path=str(artifact), sha256=digest, size=artifact.stat().st_size)))
