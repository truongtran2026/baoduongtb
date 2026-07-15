from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import get_db
from ..templating import templates
from ..utils import parse_id

router = APIRouter()


def _redirect(back_to: str, **params) -> RedirectResponse:
    base = back_to if back_to.startswith("/") else "/stations"
    return RedirectResponse(f"{base}?{urlencode(params)}", status_code=303)


@router.get("/stations", response_class=HTMLResponse)
def list_stations(request: Request, db: Session = Depends(get_db)):
    stations = db.query(models.Station).order_by(models.Station.code).all()
    device_counts = dict(
        db.query(models.Device.station_id, func.count(models.Device.id)).group_by(models.Device.station_id).all()
    )
    employee_counts = dict(
        db.query(models.Employee.station_id, func.count(models.Employee.id)).group_by(models.Employee.station_id).all()
    )
    rows = []
    for s in stations:
        rows.append(
            {
                "station": s,
                "device_count": device_counts.get(s.id, 0),
                "employee_count": employee_counts.get(s.id, 0),
            }
        )
    return templates.TemplateResponse(
        "stations.html",
        {"request": request, "rows": rows, "active_nav": "stations"},
    )


@router.get("/stations/{station_id}", response_class=HTMLResponse)
def station_detail(station_id: int, request: Request, category_id: str = "", db: Session = Depends(get_db)):
    station = db.get(models.Station, station_id)
    if station is None:
        return RedirectResponse("/stations?error=Không tìm thấy trạm", status_code=303)

    category_id = parse_id(category_id)
    employees = db.query(models.Employee).filter_by(station_id=station.id).order_by(models.Employee.name).all()

    device_query = (
        db.query(models.Device)
        .options(joinedload(models.Device.category))
        .filter(models.Device.station_id == station.id)
    )
    if category_id:
        device_query = device_query.filter(models.Device.category_id == category_id)
    devices = device_query.join(models.Category).order_by(models.Category.sort_order, models.Device.name).all()

    categories = db.query(models.Category).order_by(models.Category.sort_order).all()
    device_counts = dict(
        db.query(models.Device.category_id, func.count(models.Device.id))
        .filter(models.Device.station_id == station.id)
        .group_by(models.Device.category_id)
        .all()
    )

    return templates.TemplateResponse(
        "station_detail.html",
        {
            "request": request,
            "station": station,
            "employees": employees,
            "devices": devices,
            "categories": categories,
            "device_counts": device_counts,
            "filter_category_id": category_id,
            "active_nav": "stations",
        },
    )


@router.post("/stations")
def create_station(
    code: str = Form(...),
    name: str = Form(...),
    center: str = Form(""),
    address: str = Form(""),
    coordinates: str = Form(""),
    db: Session = Depends(get_db),
):
    code = code.strip()
    if not code or not name.strip():
        return RedirectResponse(f"/stations?error=Thiếu mã trạm hoặc tên trạm", status_code=303)
    if db.query(models.Station).filter_by(code=code).first():
        return RedirectResponse(f"/stations?error=Mã trạm '{code}' đã tồn tại", status_code=303)
    db.add(models.Station(code=code, name=name.strip(), center=center.strip(), address=address.strip(), coordinates=coordinates.strip()))
    db.commit()
    return RedirectResponse("/stations?ok=Đã thêm trạm", status_code=303)


@router.post("/stations/{station_id}/edit")
def edit_station(
    station_id: int,
    code: str = Form(...),
    name: str = Form(...),
    center: str = Form(""),
    address: str = Form(""),
    coordinates: str = Form(""),
    back_to: str = Form("/stations"),
    db: Session = Depends(get_db),
):
    station = db.get(models.Station, station_id)
    if station is None:
        return _redirect(back_to, error="Không tìm thấy trạm")
    dup = db.query(models.Station).filter(models.Station.code == code.strip(), models.Station.id != station_id).first()
    if dup:
        return _redirect(back_to, error=f"Mã trạm '{code}' đã tồn tại")
    station.code = code.strip()
    station.name = name.strip()
    station.center = center.strip()
    station.address = address.strip()
    station.coordinates = coordinates.strip()
    db.commit()
    return _redirect(back_to, ok="Đã lưu thay đổi")


@router.post("/stations/{station_id}/toggle")
def toggle_station(station_id: int, back_to: str = Form("/stations"), db: Session = Depends(get_db)):
    station = db.get(models.Station, station_id)
    if station:
        station.active = not station.active
        db.commit()
    return _redirect(back_to, ok="Đã cập nhật trạng thái")


@router.post("/stations/{station_id}/delete")
def delete_station(station_id: int, db: Session = Depends(get_db)):
    station = db.get(models.Station, station_id)
    if station is None:
        return RedirectResponse("/stations?error=Không tìm thấy trạm", status_code=303)
    try:
        db.delete(station)
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            "/stations?error=Không thể xoá: trạm đã có lịch sử tạo file. Hãy dùng 'Ngừng sử dụng' thay vì xoá.",
            status_code=303,
        )
    return RedirectResponse("/stations?ok=Đã xoá trạm", status_code=303)
