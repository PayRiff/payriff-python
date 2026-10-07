from __future__ import annotations

import re
import urllib.parse
from datetime import date, datetime
from typing import Any

MAX_PAGE_SIZE = 20

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def required(value: Any, name: str) -> Any:
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def segment(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be blank")
    return urllib.parse.quote(value, safe="")


def compact(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None and v != {}}


def format_datetime(value: datetime | str | None) -> str | None:
    if value is None or isinstance(value, str):
        return value
    return value.replace(microsecond=0, tzinfo=None).isoformat()


def filter_date(value: date | str | None, name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        m = _ISO_DATE.match(value)
        if not m:
            raise ValueError(f"{name} must be a date or a YYYY-MM-DD string")
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return value.strftime("%d.%m.%Y")


def page_query(page: int, size: int) -> dict[str, int]:
    if not isinstance(page, int) or isinstance(page, bool) or page < 0:
        raise ValueError("page must be >= 0")
    if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= MAX_PAGE_SIZE:
        raise ValueError(f"size must be 1-{MAX_PAGE_SIZE}")
    return {"page": page, "offset": size}