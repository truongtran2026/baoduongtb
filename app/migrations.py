"""One-time, idempotent schema migrations for a pre-existing LOCAL SQLite
database - specifically, one created before file content moved from local
disk into the database (needed so the same codebase can also run on a
serverless deployment with no persistent filesystem).

Only ever touches SQLite (see database.IS_SQLITE): a fresh Postgres database
is always created via models.init_db() with the current schema already in
place, so there's nothing to migrate there. Every change here is additive
(ADD COLUMN, backfill from data that already exists elsewhere) - nothing is
ever dropped or overwritten.
"""
from pathlib import Path

from sqlalchemy import inspect, text

from . import models
from .database import IS_SQLITE, SessionLocal, engine
from .docx_engine import long_path
from .paths import APP_DIR


def _column_exists(table: str, column: str) -> bool:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def _add_column(table: str, column: str, sql_type: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


def _backfill_template_content() -> None:
    legacy_dir = APP_DIR / "data" / "word_templates"
    db = SessionLocal()
    try:
        rows = db.query(models.WordTemplate).filter(models.WordTemplate.content.is_(None)).all()
        filled = 0
        for row in rows:
            src = legacy_dir / row.stored_filename
            if src.exists():
                row.content = src.read_bytes()
                filled += 1
        db.commit()
        if rows:
            print(f"[migrate] word_templates: nạp lại nội dung từ ổ đĩa cho {filled}/{len(rows)} file mẫu")
    finally:
        db.close()


def _backfill_generated_file_content() -> None:
    db = SessionLocal()
    try:
        rows = db.query(models.GeneratedFile).filter(models.GeneratedFile.content.is_(None)).all()
        filled = 0
        for row in rows:
            if not row.full_path:
                continue
            p = Path(long_path(Path(row.full_path)))
            if p.exists():
                row.content = p.read_bytes()
                filled += 1
        db.commit()
        if rows:
            print(f"[migrate] generated_files: nạp lại nội dung từ ổ đĩa cho {filled}/{len(rows)} file")
    finally:
        db.close()


def run_sqlite_migrations() -> None:
    if not IS_SQLITE:
        return

    if not _column_exists("word_templates", "content"):
        _add_column("word_templates", "content", "BLOB")
        _backfill_template_content()

    if not _column_exists("generated_files", "content"):
        _add_column("generated_files", "content", "BLOB")
        _backfill_generated_file_content()
