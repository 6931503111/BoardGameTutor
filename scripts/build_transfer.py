"""Create a portable source/data ZIP, without environments, models or secrets."""
import hashlib
import json
import platform
import sqlite3
import urllib.request
import zipfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(path):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as source, closing(sqlite3.connect(':memory:')) as target:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError(f'Database integrity check failed: {path.name}')
        return target.serialize()


def main():
    stamp = datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d-%H%M%S')
    destination = ROOT / 'backups' / f'BoardGameTutor-Windows-{stamp}.zip'
    destination.parent.mkdir(exist_ok=True)
    if not (ROOT / 'backend/data/games.sqlite3').is_file():
        raise SystemExit('No game database found; package not created.')
    files = [ROOT / 'README.md', ROOT / 'Start-BoardGameTutor.cmd']
    for directory in ('Code', 'scripts', 'Doc'):
        files += [p for p in (ROOT / directory).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix.lower() not in {'.pyc', '.log'}
                  and (directory != 'Doc' or p.suffix.lower() == '.md')]
    files += [p for p in (ROOT / 'backend').iterdir() if p.is_file() and p.suffix.lower() in {'.py', '.txt', '.json'}]
    for directory in ('backend/tests', 'backend/data/reference_manuals'):
        files += [p for p in (ROOT / directory).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix.lower() not in {'.pyc', '.log'}]
    manifest = {}
    versions = {'python': platform.python_version(), 'dependencies': {
        name: version(name) for name in ('fastapi', 'uvicorn', 'httpx', 'pypdf', 'python-multipart')},
        'models': [], 'note': 'Model files and embedding/answer caches are not included.'}
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=3) as response:
            versions['models'] = [m for m in json.load(response).get('models', [])
                                  if m['name'] in {'qwen3.5:4b', 'qwen3:1.7b', 'embeddinggemma:latest'}]
    except OSError:
        versions['note'] += ' Ollama was unavailable when recording versions.'
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        def add(name, data):
            archive.writestr('BoardGameTutor/' + name, data)
            manifest[name] = hashlib.sha256(data).hexdigest()
        for path in sorted(set(files)):
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
                raise RuntimeError(f'Unexpected source path: {path.name}')
            add(path.relative_to(ROOT).as_posix(), path.read_bytes())
        add('backend/data/games.sqlite3', snapshot(ROOT / 'backend/data/games.sqlite3'))
        add('INSTALL_WINDOWS.md', (ROOT / 'Doc/INSTALL_WINDOWS.md').read_bytes())
        add('RUNTIME_VERSIONS.json', json.dumps(versions, ensure_ascii=False, indent=2).encode('utf-8'))
        archive.writestr('BoardGameTutor/MANIFEST.sha256', ''.join(f'{digest}  {name}\n' for name, digest in sorted(manifest.items())))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Archive CRC verification failed')
    with destination.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    destination.with_suffix('.zip.sha256').write_text(digest + '  ' + destination.name + '\n', encoding='utf-8')
    print(json.dumps({'path': str(destination), 'bytes': destination.stat().st_size,
                      'files': len(manifest), 'sha256': digest}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
