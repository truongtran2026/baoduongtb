from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..paths import DEFAULT_OUTPUT_DIR
from ..settings_store import OUTPUT_ROOT_KEY, get_output_root, set_setting
from ..templating import templates

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def show_settings(request: Request, db: Session = Depends(get_db)):
    output_root = get_output_root(db)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "output_root": str(output_root),
            "default_output_root": str(DEFAULT_OUTPUT_DIR),
            "active_nav": "settings",
        },
    )


@router.post("/settings/output-root")
def update_output_root(output_root: str = Form(...), db: Session = Depends(get_db)):
    value = output_root.strip() or str(DEFAULT_OUTPUT_DIR)
    set_setting(db, OUTPUT_ROOT_KEY, value)
    return RedirectResponse("/settings?ok=Đã lưu thư mục lưu file", status_code=303)
