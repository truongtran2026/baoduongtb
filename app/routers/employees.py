from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import get_db
from ..templating import templates
from ..utils import parse_id

router = APIRouter()


def _redirect(back_to: str, **params) -> RedirectResponse:
    base = back_to if back_to.startswith("/") else "/employees"
    return RedirectResponse(f"{base}?{urlencode(params)}", status_code=303)


@router.get("/employees", response_class=HTMLResponse)
def list_employees(request: Request, station_id: str = "", q: str = "", db: Session = Depends(get_db)):
    filter_station_id = parse_id(station_id)
    query = db.query(models.Employee).options(joinedload(models.Employee.station)).join(models.Station)
    if filter_station_id:
        query = query.filter(models.Employee.station_id == filter_station_id)
    if q.strip():
        query = query.filter(models.Employee.name.ilike(f"%{q.strip()}%"))
    employees = query.order_by(models.Station.code, models.Employee.name).all()

    grand_total = db.query(models.Employee).count()
    stations = db.query(models.Station).order_by(models.Station.code).all()
    return templates.TemplateResponse(
        "employees.html",
        {
            "request": request,
            "employees": employees,
            "stations": stations,
            "filter_station_id": filter_station_id,
            "q": q,
            "total": len(employees),
            "grand_total": grand_total,
            "active_nav": "employees",
        },
    )


@router.post("/employees")
def create_employee(
    name: str = Form(...),
    station_id: int = Form(...),
    back_to: str = Form("/employees"),
    db: Session = Depends(get_db),
):
    if not name.strip():
        return _redirect(back_to, error="Thiếu tên nhân viên")
    if not db.get(models.Station, station_id):
        return _redirect(back_to, error="Trạm không hợp lệ")
    db.add(models.Employee(name=name.strip(), station_id=station_id))
    db.commit()
    return _redirect(back_to, ok="Đã thêm nhân viên")


@router.post("/employees/{employee_id}/edit")
def edit_employee(
    employee_id: int,
    name: str = Form(...),
    station_id: int = Form(...),
    back_to: str = Form("/employees"),
    db: Session = Depends(get_db),
):
    emp = db.get(models.Employee, employee_id)
    if emp is None:
        return _redirect(back_to, error="Không tìm thấy nhân viên")
    emp.name = name.strip()
    emp.station_id = station_id
    db.commit()
    return _redirect(back_to, ok="Đã lưu thay đổi")


@router.post("/employees/{employee_id}/toggle")
def toggle_employee(employee_id: int, back_to: str = Form("/employees"), db: Session = Depends(get_db)):
    emp = db.get(models.Employee, employee_id)
    if emp:
        emp.active = not emp.active
        db.commit()
    return _redirect(back_to, ok="Đã cập nhật trạng thái")


@router.post("/employees/{employee_id}/delete")
def delete_employee(employee_id: int, back_to: str = Form("/employees"), db: Session = Depends(get_db)):
    emp = db.get(models.Employee, employee_id)
    if emp is None:
        return _redirect(back_to, error="Không tìm thấy nhân viên")
    db.delete(emp)
    db.commit()
    return _redirect(back_to, ok="Đã xoá nhân viên")
