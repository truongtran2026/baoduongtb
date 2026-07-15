from datetime import date

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    station_id: int
    category_id: int
    maintenance_date: date
    performed_by: str
    coworker: str = ""
    device_ids: list[int]


class GenerateFileResult(BaseModel):
    device_name: str
    filename: str
    status: str
    message: str = ""


class GenerateResponse(BaseModel):
    run_id: int
    requested_count: int
    success_count: int
    warning_count: int
    error_count: int
    output_folder: str
    can_open_locally: bool
    files: list[GenerateFileResult]
