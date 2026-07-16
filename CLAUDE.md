# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A FastAPI web app that generates equipment-maintenance Word reports (`.docx`) from templates, for a
Vietnamese telecom network infrastructure team. It replaces a legacy Excel + VBA tool
(`taofilebdV3.0.xlsm`, not in this repo) that mail-merged station/employee/device data from Excel sheets
into Word templates via `[[placeholder]]` tags and Word's COM automation. See `README.md` (Vietnamese,
user-facing) for the full feature walkthrough.

The domain is Vietnamese and so is the UI/DB content: `trạm` = station, `nhân viên` = employee, `thiết bị`
= device, `mục bảo dưỡng` = maintenance category (Vô tuyến/Radio, Truyền dẫn/Transmission, Chuyển
mạch/Switching, IP Băng rộng/IP Broadband, plus any user-added ones).

## Running it

No test suite exists (no pytest, no `tests/`). Changes are verified by booting the app and exercising it
over HTTP (curl or a browser) - see the git log for this repo's history of exactly that pattern (start
uvicorn in the background, curl the relevant routes/API endpoints, inspect the SQLite file directly with
`sqlite3`/a one-off Python script, tear down). Do the same for any change here.

```bash
# first time
py -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt

# run (LAN mode - default, no env vars needed)
venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8899
```

`run.bat`/`setup.bat` wrap the above for a non-technical Windows user (double-click to launch); they are the
literal LAN deployment mechanism, not just dev conveniences.

Windows consoles default to `cp1252`, which cannot encode the Vietnamese text this app prints/renders -
`app/main.py` force-reconfigures stdout/stderr to UTF-8 at import time. If you add new console output,
it'll inherit that fix; if you write a standalone script outside the app, set `PYTHONUTF8=1` yourself or it
will crash on the first Vietnamese `print()`.

If testing from this machine's Git Bash: `curl`'s native Windows build mangles POSIX-looking arguments (a
leading `/something`) via MSYS2 path conversion, and silently corrupts non-ASCII (Vietnamese) query strings
passed inline. Prefix commands with `MSYS2_ARG_CONV_EXCL="*"`, or better, drive HTTP calls from Python
(`urllib.request`) instead of curl when Vietnamese text is involved.

## Architecture

### Two deployment modes, one codebase

This is the one thing that touches almost every file, so understand it before changing anything:

- **LAN mode** (default): SQLite file at `app/data/app.db`, no login. Security boundary is network access
  (only people on the office LAN can reach the server). This is what `run.bat` runs.
- **Cloud mode** (e.g. Vercel): Postgres via `DATABASE_URL`/`POSTGRES_URL`/`POSTGRES_PRISMA_URL` (checked in
  that order, see `app/database.py`), login required. Reachable from the public internet, so `auth.py`'s
  `LoginRequiredMiddleware` gates every route except `/login` and `/static/*`.

`database.IS_SQLITE` is the flag basically everything branches on: `auth.REQUIRE_LOGIN = not IS_SQLITE`,
whether `docx_engine`'s local-disk mirror is attempted, whether Settings exposes the output-folder picker,
whether "Mở thư mục" (open folder) is offered, whether the legacy-project auto-seed runs. When adding a
feature, ask which mode(s) it's meaningful in rather than assuming both.

A serverless deployment has no persistent/writable local filesystem, which is *why* mode #2 exists at all -
the first Vercel deployment crashed on exactly this (`app/paths.py` used to unconditionally `mkdir()` at
import time; now wrapped in try/except, and generated/uploaded file *content* lives in the database instead
of on disk - see below).

### File content lives in the database, not on disk

`WordTemplate.content` and `GeneratedFile.content` are `LargeBinary` columns holding the actual `.docx`
bytes. This is the real fix for running on serverless. In LAN mode, `docx_engine.generate_one()`
additionally best-effort mirrors each generated file to a real folder on disk (`app/data/output/<category
folder>/`) purely so "Mở thư mục" can point Explorer at it - that mirror is never the source of truth and a
failure to write it doesn't fail the request. Downloads (`routers/history.py`) always read from the
database column, in every mode.

`docx_engine.py` fills `[[placeholder]]` tags with a run-aware replacement (Word splits a single visible
token across multiple XML `<w:r>` runs via spellcheck/autocorrect, so a naive per-run string replace misses
tags silently). It also always writes through a `\\?\`-prefixed long path (`long_path()`) when it does touch
local disk, which is the fix for the original legacy tool's crash on long device/folder names hitting
Windows' 260-char `MAX_PATH`.

### Data model is Excel-import-driven, and reconciles on re-import

`excel_import.py` reads the same 4-sheet layout the legacy tool used (`tram`, `nhan vien`, `muc`, `thiet
bi`), and `excel_export.py` writes it back out - Export → edit in Excel → re-Import is the user's normal
workflow for bulk data maintenance (see `routers/data_io.py`), not a one-time migration path.

Import treats each sheet as *authoritative* for what it covers: for devices, every (station, category) pair
present in the sheet has its device list fully reconciled - rows missing from the sheet get hard-deleted,
not soft-deactivated. Same for employees, scoped per station. This was a deliberate, explicit product
decision (not a default I picked) - see git log around "hard delete not deactivate" for the reasoning.
Stations and categories are never auto-deleted this way (they're referenced by `generation_runs`, so a
stray deletion would break history; devices/employees have no incoming FK, so hard-deleting them is safe).

Every `import_*` function loads its existing rows with one query up front and matches in memory, rather
than querying per Excel row - this used to be a real N+1 (300+ devices = 300+ round trips), invisible
against local SQLite but easily enough to blow a serverless function's execution time limit against a
networked Postgres database. If you add a new bulk-import path, follow the same load-once pattern.

Categories (equipment types) are data-driven rows, not a hardcoded enum - adding "Nguồn điện" (power
equipment) as a new category + uploading its own `.docx` template is a normal user action through the UI
(`routers/categories.py`), not a code change. `FOLDER_AND_PREFIX_BY_CODE` in `excel_import.py` only supplies
cosmetic defaults (output folder name, filename prefix) for the four categories the legacy tool shipped
with; anything else falls back to a sensible default derived from the category name/code.

### Known SQLAlchemy/Python gotcha

`Mapped[bytes | None]` (PEP 604 union syntax in a SQLAlchemy 2.0 declarative column) crashes at
class-definition time on this project's Python 3.14 + SQLAlchemy 2.0.35 combination
(`TypeError: descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'`). Nullable
binary columns in `models.py` use `Mapped[bytes] = mapped_column(LargeBinary, nullable=True)` instead - the
type hint is slightly optimistic but `nullable=True` is what actually controls the database column, and
that's authoritative. Don't reintroduce `X | None` inside `Mapped[]` without checking this still reproduces.

### Schema migrations for the existing LAN database

There is no migration framework (no Alembic). `models.init_db()` (`Base.metadata.create_all`) only creates
*missing tables*, never alters existing ones - so a genuinely new column on an existing table needs an
explicit, hand-written, idempotent migration in `migrations.py` (`ALTER TABLE ... ADD COLUMN`, then backfill
from wherever the data used to live). This only ever runs for SQLite (`run_sqlite_migrations`); a fresh
Postgres database is always created via `init_db()` with the current schema already in place, so there's
nothing to migrate there. Every change so far has been additive/backfill-only - never drop a column this
way, since an existing LAN database has real production data in it and the safe pattern is "add a nullable
column, keep the old one around unused" rather than trying to remove anything (see `Device.active` in
`models.py` for the previous instance of this: removing it from the model without a matching migration
broke every INSERT, because the physical SQLite column was still `NOT NULL` with no default).

### Router layout

One router module per resource under `app/routers/`, each owning both its HTML pages (Jinja2 via
`templating.py`) and its JSON API endpoints where it has any (`generate.py`'s `/api/generate/*` for the
cascading station→category→device pickers on the main page). `stations.py` additionally owns
`/stations/{id}`, a per-station "folder" page that embeds that station's own employee/device management
inline rather than linking out to the global list pages.

Mutating routers accept an optional `back_to` form field so an action triggered from a station's own page
redirects back there instead of always bouncing to the global list page; see the `_redirect()` helper
duplicated (deliberately, not shared) in a few routers.
