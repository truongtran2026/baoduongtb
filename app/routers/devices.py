from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import get_db
from ..templating import templates
from ..utils import parse_id

router = APIRouter()

PAGE_SIZE = 150


def _redirect(back_to: str, **params) -> RedirectResponse:
    """Send the user back to wherever they triggered the action from (the
    global Devices page, or a station's own detail page) instead of always
    jumping to /devices."""
    base = back_to if back_to.startswith("/") else "/devices"
    return RedirectResponse(f"{base}?{urlencode(params)}", status_code=303)


DEFAULT_STATION_CODE = "ADN1"


@router.get("/devices", response_class=HTMLResponse)
def list_devices(
    request: Request,
    station_id: str | None = None,
    category_id: str = "",
    q: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):
    if station_id is None:
        # Fresh visit (no filter in the URL at all, as opposed to the user
        # explicitly picking "Tất cả trạm" which sends station_id=""): default
        # to the station most people are working with instead of a 300+ row
        # unfiltered dump.
        default_station = db.query(models.Station).filter_by(code=DEFAULT_STATION_CODE).first()
        station_id = default_station.id if default_station else None
    else:
        station_id = parse_id(station_id)
    category_id = parse_id(category_id)

    grand_total = db.query(models.Device).count()
    query = db.query(models.Device).options(joinedload(models.Device.station), joinedload(models.Device.category))
    if station_id:
        query = query.filter(models.Device.station_id == station_id)
    if category_id:
        query = query.filter(models.Device.category_id == category_id)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(models.Device.name.ilike(like))

    total = query.count()
    page = max(1, page)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    devices = (
        query.join(models.Station)
        .order_by(models.Station.code, models.Device.name)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    stations = db.query(models.Station).order_by(models.Station.code).all()
    categories = db.query(models.Category).order_by(models.Category.sort_order).all()

    return templates.TemplateResponse(
        "devices.html",
        {
            "request": request,
            "devices": devices,
            "stations": stations,
            "categories": categories,
            "filter_station_id": station_id,
            "filter_category_id": category_id,
            "q": q,
            "total": total,
            "grand_total": grand_total,
            "page": page,
            "total_pages": total_pages,
            "active_nav": "devices",
        },
    )


@router.post("/devices")
def create_device(
    station_id: int = Form(...),
    category_id: int = Form(...),
    name: str = Form(...),
    record_no: str = Form(""),
    configuration: str = Form(""),
    back_to: str = Form("/devices"),
    db: Session = Depends(get_db),
):
    if not name.strip():
        return _redirect(back_to, error="Thiếu tên thiết bị")
    db.add(
        models.Device(
            station_id=station_id,
            category_id=category_id,
            name=name.strip(),
            record_no=record_no.strip(),
            configuration=configuration.strip(),
        )
    )
    db.commit()
    return _redirect(back_to, ok="Đã thêm thiết bị")


@router.post("/devices/{device_id}/edit")
def edit_device(
    device_id: int,
    station_id: int = Form(...),
    category_id: int = Form(...),
    name: str = Form(...),
    record_no: str = Form(""),
    configuration: str = Form(""),
    back_to: str = Form("/devices"),
    db: Session = Depends(get_db),
):
    device = db.get(models.Device, device_id)
    if device is None:
        return _redirect(back_to, error="Không tìm thấy thiết bị")
    device.station_id = station_id
    device.category_id = category_id
    device.name = name.strip()
    device.record_no = record_no.strip()
    device.configuration = configuration.strip()
    db.commit()
    return _redirect(back_to, ok="Đã lưu thay đổi")


@router.post("/devices/{device_id}/delete")
def delete_device(device_id: int, back_to: str = Form("/devices"), db: Session = Depends(get_db)):
    device = db.get(models.Device, device_id)
    if device is None:
        return _redirect(back_to, error="Không tìm thấy thiết bị")
    db.delete(device)
    db.commit()
    return _redirect(back_to, ok="Đã xoá thiết bị")


@router.post("/devices/bulk-delete")
def bulk_delete_devices(
    device_ids: list[int] = Form(default=[]),
    back_to: str = Form("/devices"),
    db: Session = Depends(get_db),
):
    if not device_ids:
        return _redirect(back_to, error="Chưa chọn thiết bị nào")
    count = (
        db.query(models.Device)
        .filter(models.Device.id.in_(device_ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    return _redirect(back_to, ok=f"Đã xoá {count} thiết bị")
