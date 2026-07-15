import os
import socket
import sys

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# Windows consoles default to the system codepage (e.g. cp1252), which cannot
# encode Vietnamese text and crashes any print() of it. Force UTF-8 output
# regardless of how this process is launched (run.bat, PowerShell, a plain
# terminal, ...). Harmless no-op on platforms where stdout is already UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from . import models
from .auth import LoginRequiredMiddleware, REQUIRE_LOGIN, get_session_secret, hash_password
from .database import IS_SQLITE, SessionLocal
from .excel_import import import_from_workbook, seed_word_templates
from .migrations import run_sqlite_migrations
from .paths import APP_DIR
from .routers import auth, categories, data_io, devices, employees, generate, history, settings, stations

APP_TITLE = "Bảo dưỡng thiết bị - Tạo hồ sơ bảo dưỡng"

app = FastAPI(title=APP_TITLE)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

# Order matters: added last = outermost = runs first on each request, so
# SessionMiddleware (which populates request.session) must be added *after*
# LoginRequiredMiddleware (which reads it) to run before it.
app.add_middleware(LoginRequiredMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    same_site="lax",
    https_only=not IS_SQLITE,
    max_age=60 * 60 * 24 * 7,
)

for router in (
    auth.router, stations.router, employees.router, categories.router, devices.router,
    generate.router, history.router, settings.router, data_io.router,
):
    app.include_router(router)


@app.get("/")
def root():
    return RedirectResponse("/generate")


def _auto_seed_from_legacy_project() -> None:
    """First-run convenience for the LAN deployment: if the DB is empty and
    the old VBA project (taofilebdV3.0.xlsm + Temp\\*.docx) is sitting next
    to this app on local disk, import it automatically so the new app is
    usable immediately instead of starting blank. Meaningless in cloud mode
    (no such local folder exists there), so skip outright.
    """
    if not IS_SQLITE:
        return

    legacy_dir = APP_DIR.parent.parent / "ProjectBDTB_Old"
    legacy_xlsm = legacy_dir / "taofilebdV3.0.xlsm"
    legacy_templates = legacy_dir / "Temp"
    if not legacy_xlsm.exists():
        return

    db = SessionLocal()
    try:
        if db.query(models.Station).count() > 0:
            return  # already has data, never auto-import over it
        summary = import_from_workbook(db, legacy_xlsm)
        if legacy_templates.exists():
            seed_word_templates(db, legacy_templates, summary)
        print(
            f"[seed] Imported from legacy project: {summary.stations} trạm, "
            f"{summary.employees} nhân viên, {summary.categories} mục, "
            f"{summary.devices} thiết bị, {summary.templates} file mẫu"
        )
        for w in summary.warnings:
            print(f"[seed][warning] {w}")
    except Exception as exc:  # noqa: BLE001 - seeding must never block app startup
        print(f"[seed] Bỏ qua auto-seed do lỗi: {exc}")
    finally:
        db.close()


def _bootstrap_admin_user() -> None:
    """Cloud mode only: create the first login from ADMIN_USERNAME /
    ADMIN_PASSWORD env vars if no account exists yet. LAN mode has no login
    at all (REQUIRE_LOGIN is False there), so this is a no-op there."""
    if not REQUIRE_LOGIN:
        return
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            return
        admin_username = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not admin_username or not admin_password:
            print(
                "[auth][warning] Chưa có tài khoản nào và thiếu biến môi trường "
                "ADMIN_USERNAME/ADMIN_PASSWORD - hãy đặt 2 biến này rồi triển khai lại "
                "để tạo tài khoản quản trị đầu tiên."
            )
            return
        db.add(
            models.User(
                username=admin_username.strip(),
                password_hash=hash_password(admin_password),
                display_name=admin_username.strip(),
            )
        )
        db.commit()
        print(f"[auth] Đã tạo tài khoản quản trị đầu tiên: {admin_username}")
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    models.init_db()
    run_sqlite_migrations()
    _auto_seed_from_legacy_project()
    _bootstrap_admin_user()

    if IS_SQLITE:
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            lan_ip = "?"
        print("=" * 60)
        print(f"  {APP_TITLE}")
        print("  Máy này:        http://127.0.0.1:8899")
        print(f"  Máy khác (LAN): http://{lan_ip}:8899")
        print("=" * 60)
    else:
        print("=" * 60)
        print(f"  {APP_TITLE} (cloud mode, đăng nhập bắt buộc)")
        print("=" * 60)
