import uuid

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..templating import templates

router = APIRouter()


@router.get("/categories", response_class=HTMLResponse)
def list_categories(request: Request, db: Session = Depends(get_db)):
    categories = db.query(models.Category).order_by(models.Category.sort_order, models.Category.name).all()
    device_counts = dict(
        db.query(models.Device.category_id, func.count(models.Device.id)).group_by(models.Device.category_id).all()
    )
    rows = []
    for c in categories:
        active_template = (
            db.query(models.WordTemplate).filter_by(category_id=c.id, is_active=True).order_by(models.WordTemplate.uploaded_at.desc()).first()
        )
        rows.append(
            {
                "category": c,
                "device_count": device_counts.get(c.id, 0),
                "template": active_template,
            }
        )
    return templates.TemplateResponse(
        "categories.html",
        {"request": request, "rows": rows, "active_nav": "categories"},
    )


@router.post("/categories")
def create_category(
    name: str = Form(...),
    code: str = Form(...),
    output_folder_name: str = Form(...),
    filename_prefix: str = Form(...),
    db: Session = Depends(get_db),
):
    code = code.strip().upper()
    if not name.strip() or not code:
        return RedirectResponse("/categories?error=Thiếu tên hoặc mã mục bảo dưỡng", status_code=303)
    if db.query(models.Category).filter_by(code=code).first():
        return RedirectResponse(f"/categories?error=Mã '{code}' đã tồn tại", status_code=303)
    max_order = db.query(func.max(models.Category.sort_order)).scalar() or 0
    db.add(
        models.Category(
            name=name.strip(),
            code=code,
            output_folder_name=output_folder_name.strip() or name.strip(),
            filename_prefix=filename_prefix.strip() or f"{code}-C3-M",
            sort_order=max_order + 1,
        )
    )
    db.commit()
    return RedirectResponse("/categories?ok=Đã thêm mục bảo dưỡng", status_code=303)


@router.post("/categories/{category_id}/edit")
def edit_category(
    category_id: int,
    name: str = Form(...),
    code: str = Form(...),
    output_folder_name: str = Form(...),
    filename_prefix: str = Form(...),
    db: Session = Depends(get_db),
):
    cat = db.get(models.Category, category_id)
    if cat is None:
        return RedirectResponse("/categories?error=Không tìm thấy mục bảo dưỡng", status_code=303)
    code = code.strip().upper()
    dup = db.query(models.Category).filter(models.Category.code == code, models.Category.id != category_id).first()
    if dup:
        return RedirectResponse(f"/categories?error=Mã '{code}' đã tồn tại", status_code=303)
    cat.name = name.strip()
    cat.code = code
    cat.output_folder_name = output_folder_name.strip()
    cat.filename_prefix = filename_prefix.strip()
    db.commit()
    return RedirectResponse("/categories?ok=Đã lưu thay đổi", status_code=303)


@router.post("/categories/{category_id}/toggle")
def toggle_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if cat:
        cat.active = not cat.active
        db.commit()
    return RedirectResponse("/categories?ok=Đã cập nhật trạng thái", status_code=303)


@router.post("/categories/{category_id}/delete")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if cat is None:
        return RedirectResponse("/categories?error=Không tìm thấy mục bảo dưỡng", status_code=303)
    try:
        db.delete(cat)
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            "/categories?error=Không thể xoá: mục này đã có thiết bị hoặc lịch sử tạo file. Hãy dùng 'Ngừng sử dụng'.",
            status_code=303,
        )
    return RedirectResponse("/categories?ok=Đã xoá mục bảo dưỡng", status_code=303)


@router.post("/categories/{category_id}/template")
async def upload_template(category_id: int, template_file: UploadFile, db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if cat is None:
        return RedirectResponse("/categories?error=Không tìm thấy mục bảo dưỡng", status_code=303)
    if not template_file.filename.lower().endswith(".docx"):
        return RedirectResponse("/categories?error=File mẫu phải có định dạng .docx", status_code=303)

    content = await template_file.read()

    db.query(models.WordTemplate).filter_by(category_id=category_id, is_active=True).update({"is_active": False})
    db.add(
        models.WordTemplate(
            category_id=category_id,
            original_filename=template_file.filename,
            stored_filename=f"{uuid.uuid4().hex}.docx",
            content=content,
            is_active=True,
        )
    )
    db.commit()
    return RedirectResponse("/categories?ok=Đã cập nhật file mẫu Word", status_code=303)
