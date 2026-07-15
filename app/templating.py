from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def format_date_vn(value) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def format_datetime_vn(value) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")


templates.env.filters["vndate"] = format_date_vn
templates.env.filters["vndatetime"] = format_datetime_vn
