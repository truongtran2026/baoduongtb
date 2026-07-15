"""Vercel Python entrypoint - just re-exports the FastAPI app. Vercel's
Python runtime detects the module-level `app` object and wraps it to serve
ASGI requests; nothing else needs to happen in this file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401
