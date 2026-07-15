"""Central place for filesystem locations used by the app."""
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
WORD_TEMPLATES_DIR = DATA_DIR / "word_templates"
DEFAULT_OUTPUT_DIR = DATA_DIR / "output"

DATA_DIR.mkdir(parents=True, exist_ok=True)
WORD_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
