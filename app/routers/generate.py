from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import docx_engine, models, schemas
from ..database import IS_SQLITE, get_db
from ..settings_store import get_output_root
from ..templating import templates

router = APIRouter()

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


@router.get("/generate", response_class=HTMLResponse)
def generate_page(request: Request, db: Session = Depends(get_db)):
    stations = db.query(models.Station).filter_by(active=True).order_by(models.Station.code).all()
    return templates.TemplateResponse(
        "generate.html",
        {"request": request, "stations": stations, "active_nav": "generate", "today": date.today().isoformat()},
    )


@router.get("/api/generate/categories")
def api_categories_for_station(station_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(models.Category, func.count(models.Device.id))
        .join(models.Device, models.Device.category_id == models.Category.id)
        .filter(
            models.Device.station_id == station_id,
            models.Category.active.is_(True),
        )
        .group_by(models.Category.id)
        .order_by(models.Category.sort_order)
        .all()
    )
    has_template_ids = {
        cid
        for (cid,) in db.query(models.WordTemplate.category_id).filter_by(is_active=True).distinct()
    }
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "code": cat.code,
            "device_count": count,
            "has_template": cat.id in has_template_ids,
        }
        for cat, count in rows
    ]


@router.get("/api/generate/employees")
def api_employees_for_station(station_id: int, db: Session = Depends(get_db)):
    employees = (
        db.query(models.Employee)
        .filter_by(station_id=station_id, active=True)
        .order_by(models.Employee.name)
        .all()
    )
    return [{"id": e.id, "name": e.name} for e in employees]


@router.get("/api/generate/devices")
def api_devices_for_selection(station_id: int, category_id: int, db: Session = Depends(get_db)):
    devices = (
        db.query(models.Device)
        .filter_by(station_id=station_id, category_id=category_id)
        .order_by(models.Device.name)
        .all()
    )
    return [
        {"id": d.id, "name": d.name, "record_no": d.record_no, "configuration": d.configuration}
        for d in devices
    ]


@router.post("/api/generate/run", response_model=schemas.GenerateResponse)
def run_generate(payload: schemas.GenerateRequest, request: Request, db: Session = Depends(get_db)):
    station = db.get(models.Station, payload.station_id)
    category = db.get(models.Category, payload.category_id)
    if station is None or category is None:
        return JSONResponse({"detail": "Trạm hoặc mục bảo dưỡng không hợp lệ"}, status_code=400)

    performed_by = payload.performed_by.strip()
    coworker = payload.coworker.strip()
    if not performed_by:
        return JSONResponse({"detail": "Thiếu Người thực hiện"}, status_code=400)
    if coworker and coworker == performed_by:
        return JSONResponse({"detail": "Người phối hợp phải khác Người thực hiện"}, status_code=400)

    template_row = (
        db.query(models.WordTemplate).filter_by(category_id=category.id, is_active=True).first()
    )
    if template_row is None or not template_row.content:
        return JSONResponse(
            {"detail": f"Mục '{category.name}' chưa có file mẫu Word. Hãy tải lên ở trang Mục bảo dưỡng."},
            status_code=400,
        )

    devices = (
        db.query(models.Device)
        .filter(
            models.Device.id.in_(payload.device_ids),
            models.Device.station_id == station.id,
            models.Device.category_id == category.id,
        )
        .all()
    )
    if not devices:
        return JSONResponse({"detail": "Không có thiết bị nào được chọn"}, status_code=400)

    output_dir = get_output_root(db) / category.output_folder_name if IS_SQLITE else None
    output_folder_display = (
        str(output_dir.resolve()) if output_dir is not None
        else "Lưu trong cơ sở dữ liệu (không có thư mục cục bộ ở chế độ cloud)"
    )

    run = models.GenerationRun(
        station_id=station.id,
        category_id=category.id,
        maintenance_date=payload.maintenance_date,
        performed_by=performed_by,
        coworker=coworker,
        requested_count=len(devices),
        output_folder=output_folder_display,
    )
    db.add(run)
    db.flush()

    station_full_name = f"{station.name} - {station.center}" if station.center else station.name
    success = warning = error = 0
    file_results: list[schemas.GenerateFileResult] = []

    for device in devices:
        mapping = {
            "matram": station.code,
            "tentram": station_full_name,
            "diachi": station.address,
            "toado": station.coordinates,
            "mucbaoduong": category.name,
            "thietbi": device.name,
            "sohs": device.record_no,
            "cauhinh": device.configuration,
            "ngaybaoduong": payload.maintenance_date.strftime("%d/%m/%Y"),
            "thangbaoduong": payload.maintenance_date.strftime("%m/%Y"),
            "nguoithuchien": performed_by,
            "nguoiphoihop": coworker,
        }
        result = docx_engine.generate_one(
            template_bytes=template_row.content,
            output_dir=output_dir,
            prefix=category.filename_prefix,
            maintenance_date=payload.maintenance_date,
            device_name=device.name,
            station_code=station.code,
            mapping=mapping,
        )
        if result.status == "success":
            success += 1
        elif result.status == "warning":
            warning += 1
        else:
            error += 1

        db.add(
            models.GeneratedFile(
                run_id=run.id,
                device_name_snapshot=device.name,
                filename=result.filename,
                full_path=result.full_path,
                content=result.content,
                status=result.status,
                message=result.message,
            )
        )
        file_results.append(
            schemas.GenerateFileResult(
                device_name=device.name, filename=result.filename, status=result.status, message=result.message
            )
        )

    run.success_count = success
    run.warning_count = warning
    run.error_count = error
    db.commit()

    client_host = request.client.host if request.client else ""
    return schemas.GenerateResponse(
        run_id=run.id,
        requested_count=len(devices),
        success_count=success,
        warning_count=warning,
        error_count=error,
        output_folder=output_folder_display,
        can_open_locally=IS_SQLITE and client_host in LOOPBACK_HOSTS,
        files=file_results,
    )
