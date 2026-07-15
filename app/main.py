import socket
import sys

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Windows consoles default to the system codepage (e.g. cp1252), which cannot
# encode Vietnamese text and crashes any print() of it. Force UTF-8 output
# regardless of how this process is launched (run.bat, PowerShell, a plain
# terminal, ...).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from . import models
from .database import SessionLocal
from .excel_import import import_from_workbook, seed_word_templates
from .paths import APP_DIR, WORD_TEMPLATES_DIR
from .routers import categories, data_io, devices, employees, generate, history, settings, stations

APP_TITLE = "Bảo dưỡng thiết bị - Tạo hồ sơ bảo dưỡng"

app = FastAPI(title=APP_TITLE)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

for router in (
    stations.router, employees.router, categories.router, devices.router,
    generate.router, history.router, settings.router, data_io.router,
):
    app.include_router(router)


@app.get("/")
def root():
    return RedirectResponse("/generate")


def _auto_seed_from_legacy_project() -> None:
    """First-run convenience: if the DB is empty and the old VBA project
    (taofilebdV3.0.xlsm + Temp\\*.docx) is sitting next to this app, import it
    automatically so the new app is usable immediately instead of starting blank.
    """
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
            seed_word_templates(db, legacy_templates, WORD_TEMPLATES_DIR, summary)
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


@app.on_event("startup")
def on_startup():
    models.init_db()
    _auto_seed_from_legacy_project()
    try:
        lan_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        lan_ip = "?"
    print("=" * 60)
    print(f"  {APP_TITLE}")
    print("  Máy này:        http://127.0.0.1:8899")
    print(f"  Máy khác (LAN): http://{lan_ip}:8899")
    print("=" * 60)
