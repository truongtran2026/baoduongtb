"""Central place for filesystem locations used by the app.

These are only ever *written to* in LAN mode (see docx_engine.py's
best-effort local mirror and database.py's SQLite fallback) - a serverless
deployment's filesystem is read-only, so creating them must never be allowed
to crash the app at import time.
"""
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
DEFAULT_OUTPUT_DIR = DATA_DIR / "output"

for _dir in (DATA_DIR, DEFAULT_OUTPUT_DIR):
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # read-only filesystem (serverless) - nothing in this mode needs these to exist
