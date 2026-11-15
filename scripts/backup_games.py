"""Consistent SQLite backup, including WAL, without stopping the application."""
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / 'backend' / 'data' / 'games.sqlite3'
if not source.is_file():
    raise SystemExit('No game database found; start the backend first.')
destination = root / 'backend' / 'data' / ('games-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.sqlite3')
with closing(sqlite3.connect(source)) as original, closing(sqlite3.connect(destination)) as backup:
    original.backup(backup)
print(destination)
