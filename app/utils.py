def parse_id(raw: str) -> int | None:
    """Query params coming from a <select> with a "Tất cả" (any) option whose
    value is "" arrive here as e.g. station_id= — an empty string, not a
    missing param, so FastAPI's `int | None` query binding can't parse it.
    Treat blank/non-numeric as "no filter" instead of a 422."""
    raw = (raw or "").strip()
    return int(raw) if raw.isdigit() else None
