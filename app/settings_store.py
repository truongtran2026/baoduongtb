from pathlib import Path

from sqlalchemy.orm import Session

from . import models
from .paths import DEFAULT_OUTPUT_DIR

OUTPUT_ROOT_KEY = "output_root"


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(models.AppSetting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(models.AppSetting, key)
    if row is None:
        row = models.AppSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()


def get_output_root(db: Session) -> Path:
    raw = get_setting(db, OUTPUT_ROOT_KEY, str(DEFAULT_OUTPUT_DIR))
    return Path(raw)
