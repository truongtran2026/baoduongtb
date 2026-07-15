from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, engine


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    center: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    coordinates: Mapped[str] = mapped_column(String(255), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="station", cascade="all, delete-orphan")
    devices: Mapped[list["Device"]] = relationship(back_populates="station", cascade="all, delete-orphan")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    station: Mapped["Station"] = relationship(back_populates="employees")


class Category(Base):
    """Mục bảo dưỡng / loại thiết bị (Vô tuyến, Truyền dẫn, Chuyển mạch, IP băng rộng, ...).

    Deliberately data-driven (not hardcoded) so new equipment groups can be
    added from the UI instead of requiring a code change.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    output_folder_name: Mapped[str] = mapped_column(String(255))
    filename_prefix: Mapped[str] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    devices: Mapped[list["Device"]] = relationship(back_populates="category")
    templates: Mapped[list["WordTemplate"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class Device(Base):
    """Devices that go away are deleted outright (see excel_import.import_devices
    and routers/devices.py bulk delete), not soft-deactivated - a device list
    that's always "what's actually there" is less confusing than one mixing
    live and retired rows.

    `active` is not used anywhere (no toggle, no filter, no UI for it) and is
    always True - it stays mapped here only because the underlying SQLite
    column is NOT NULL with no server-side default, so omitting it from the
    model would make every INSERT fail. Dropping the column outright would
    need a schema migration on a database that already has real data in it;
    keeping a dead-but-harmless column is the lower-risk fix.
    """

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(255))
    record_no: Mapped[str] = mapped_column(String(100), default="")
    configuration: Mapped[str] = mapped_column(String(255), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    station: Mapped["Station"] = relationship(back_populates="devices")
    category: Mapped["Category"] = relationship(back_populates="devices")


class WordTemplate(Base):
    __tablename__ = "word_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship(back_populates="templates")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class GenerationRun(Base):
    __tablename__ = "generation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    maintenance_date: Mapped[date] = mapped_column(Date)
    performed_by: Mapped[str] = mapped_column(String(255))
    coworker: Mapped[str] = mapped_column(String(255))
    requested_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    output_folder: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    station: Mapped["Station"] = relationship()
    category: Mapped["Category"] = relationship()
    files: Mapped[list["GeneratedFile"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("generation_runs.id"))
    device_name_snapshot: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(Text)
    full_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))  # success | warning | error
    message: Mapped[str] = mapped_column(Text, default="")

    run: Mapped["GenerationRun"] = relationship(back_populates="files")


def init_db():
    Base.metadata.create_all(bind=engine)
