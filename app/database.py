import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .paths import DB_PATH


def _resolve_database_url() -> str:
    """LAN/offline mode (default): a local SQLite file, as before.
    Cloud mode (Vercel etc.): whichever Postgres connection string the host
    injects. Hosts commonly hand out a bare postgres:// URL meant for
    generic clients - SQLAlchemy needs the driver named explicitly."""
    for var in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL"):
        raw = os.environ.get(var)
        if not raw:
            continue
        if raw.startswith("postgres://"):
            return "postgresql+psycopg://" + raw[len("postgres://"):]
        if raw.startswith("postgresql://") and "+psycopg" not in raw:
            return "postgresql+psycopg://" + raw[len("postgresql://"):]
        return raw
    return f"sqlite:///{DB_PATH}"


DATABASE_URL = _resolve_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

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
