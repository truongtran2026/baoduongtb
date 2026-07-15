import io
import subprocess
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import IS_SQLITE, get_db
from ..docx_engine import long_path
from ..templating import templates

router = APIRouter()

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _delete_runs(db: Session, run_ids: list[int]) -> int:
    """Deletes the GenerationRun/GeneratedFile rows (which is where the file
    content actually lives now) plus, best-effort, any local disk mirror
    from the LAN deployment - a file already moved/removed by the user, or
    one that was never written to disk in cloud mode, shouldn't block
    cleanup either way."""
    runs = db.query(models.GenerationRun).filter(models.GenerationRun.id.in_(run_ids)).all()
    for run in runs:
        if IS_SQLITE:
            for f in run.files:
                if f.status in ("success", "warning") and f.full_path:
                    Path(long_path(Path(f.full_path))).unlink(missing_ok=True)
        db.delete(run)
    db.commit()
    return len(runs)


@router.get("/history", response_class=HTMLResponse)
def list_history(request: Request, db: Session = Depends(get_db)):
    runs = (
        db.query(models.GenerationRun)
        .options(joinedload(models.GenerationRun.station), joinedload(models.GenerationRun.category))
        .order_by(models.GenerationRun.created_at.desc())
        .limit(200)
        .all()
    )
    return templates.TemplateResponse(
        "history.html", {"request": request, "runs": runs, "active_nav": "history"}
    )


@router.get("/history/{run_id}", response_class=HTMLResponse)
def run_detail(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = db.get(models.GenerationRun, run_id)
    if run is None:
        return RedirectResponse("/history?error=Không tìm thấy lượt tạo file", status_code=303)
    files = db.query(models.GeneratedFile).filter_by(run_id=run_id).order_by(models.GeneratedFile.filename).all()
    can_open_locally = IS_SQLITE and (request.client.host if request.client else "") in LOOPBACK_HOSTS
    return templates.TemplateResponse(
        "history_detail.html",
        {"request": request, "run": run, "files": files, "can_open_locally": can_open_locally, "active_nav": "history"},
    )


@router.post("/history/{run_id}/delete")
def delete_run(run_id: int, db: Session = Depends(get_db)):
    _delete_runs(db, [run_id])
    return RedirectResponse("/history?ok=Đã xoá lượt tạo file", status_code=303)


@router.post("/history/bulk-delete")
def bulk_delete_runs(run_ids: list[int] = Form(default=[]), db: Session = Depends(get_db)):
    if not run_ids:
        return RedirectResponse("/history?error=Chưa chọn lượt nào", status_code=303)
    count = _delete_runs(db, run_ids)
    return RedirectResponse(f"/history?ok=Đã xoá {count} lượt tạo file", status_code=303)


@router.post("/history/{run_id}/open-folder")
def open_folder(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = db.get(models.GenerationRun, run_id)
    client_host = request.client.host if request.client else ""
    if IS_SQLITE and run and client_host in LOOPBACK_HOSTS and Path(run.output_folder).exists():
        subprocess.Popen(["explorer.exe", run.output_folder])
    return RedirectResponse(f"/history/{run_id}", status_code=303)


@router.get("/history/{run_id}/download")
def download_run_zip(run_id: int, db: Session = Depends(get_db)):
    run = db.get(models.GenerationRun, run_id)
    if run is None:
        return RedirectResponse("/history?error=Không tìm thấy lượt tạo file", status_code=303)
    files = (
        db.query(models.GeneratedFile)
        .filter(models.GeneratedFile.run_id == run_id, models.GeneratedFile.status.in_(["success", "warning"]))
        .all()
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f.content:
                zf.writestr(f.filename, f.content)
    buffer.seek(0)
    zip_name = f"baoduong_run_{run_id}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


@router.get("/history/{run_id}/files/{file_id}/download")
def download_single_file(run_id: int, file_id: int, db: Session = Depends(get_db)):
    f = db.query(models.GeneratedFile).filter_by(id=file_id, run_id=run_id).first()
    if f is None or not f.content:
        return RedirectResponse(f"/history/{run_id}?error=Không tìm thấy file", status_code=303)
    return Response(
        content=f.content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{f.filename}"'},
    )
