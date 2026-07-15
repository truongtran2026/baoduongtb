import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from .. import excel_export
from ..database import get_db
from ..excel_import import ImportSummary, import_from_workbook

router = APIRouter()


@router.get("/export-excel")
def export_excel(db: Session = Depends(get_db)):
    content = excel_export.build_workbook_bytes(db)
    filename = f"baoduong_du_lieu_{date.today():%Y%m%d}.xlsx"
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import-excel")
async def import_excel(excel_file: UploadFile, back_to: str = "/devices", db: Session = Depends(get_db)):
    redirect_base = back_to if back_to.startswith("/") else "/devices"
    if not excel_file.filename.lower().endswith((".xlsx", ".xlsm")):
        return RedirectResponse(f"{redirect_base}?error=File phải có định dạng .xlsx hoặc .xlsm", status_code=303)
    content = await excel_file.read()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        summary: ImportSummary = import_from_workbook(db, tmp_path)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"{redirect_base}?error=Lỗi nhập dữ liệu: {exc}", status_code=303)
    finally:
        tmp_path.unlink(missing_ok=True)

    msg = (
        f"Đã nhập: {summary.stations} trạm, {summary.employees} nhân viên, "
        f"{summary.categories} mục bảo dưỡng, {summary.devices} thiết bị"
    )
    if summary.devices_deleted:
        msg += f", đã xoá {summary.devices_deleted} thiết bị không còn trong file"
    if summary.employees_deleted:
        msg += f", đã xoá {summary.employees_deleted} nhân viên không còn trong file"
    if summary.warnings:
        msg += f" ({len(summary.warnings)} cảnh báo)"
    return RedirectResponse(f"{redirect_base}?ok={msg}", status_code=303)
