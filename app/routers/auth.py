from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..auth import verify_password
from ..database import get_db
from ..templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/generate", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter_by(username=username.strip()).first()
    if user is None or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=Sai tên đăng nhập hoặc mật khẩu", status_code=303)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse("/generate", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
