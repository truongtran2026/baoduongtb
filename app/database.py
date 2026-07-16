import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .paths import DB_PATH

CANDIDATE_VARS = ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL")


def _resolve_database_url() -> str:
    """LAN/offline mode (default): a local SQLite file, as before.
    Cloud mode (Vercel etc.): whichever Postgres connection string the host
    injects. Hosts commonly hand out a bare postgres:// URL meant for
    generic clients - SQLAlchemy needs the driver named explicitly."""
    for var in CANDIDATE_VARS:
        raw = os.environ.get(var)
        if not raw:
            continue
        if raw.startswith("postgres://"):
            return "postgresql+psycopg://" + raw[len("postgres://"):]
        if raw.startswith("postgresql://") and "+psycopg" not in raw:
            return "postgresql+psycopg://" + raw[len("postgresql://"):]
        return raw

    if os.environ.get("VERCEL"):
        # Running on Vercel with no DB connection string found - this is a
        # misconfiguration (a serverless deployment can't use the SQLite
        # fallback, there's no persistent disk), not a normal state. Fail
        # loudly and diagnostically here instead of letting it surface later
        # as a cryptic "unable to open database file" from SQLite.
        found = sorted(
            k for k in os.environ
            if "DATABASE" in k.upper() or "POSTGRES" in k.upper()
        )
        raise RuntimeError(
            "Đang chạy trên Vercel nhưng không tìm thấy biến kết nối database. "
            f"Đã kiểm tra các tên: {', '.join(CANDIDATE_VARS)}. "
            f"Các biến môi trường có chứa DATABASE/POSTGRES hiện có: {found or '(không có)'}. "
            "Kiểm tra lại Environment Variables trong Vercel: đúng tên biến, đã tick môi trường "
            "Production, và đã Redeploy sau khi thêm/sửa biến."
        )

    return f"sqlite:///{DB_PATH}"


DATABASE_URL = _resolve_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

print(f"[database] chế độ: {'SQLite (LAN)' if IS_SQLITE else 'Postgres (cloud)'}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
