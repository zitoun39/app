"""General helper utilities used by routes."""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from flask import Request, request

from lims.models.user import User


def generate_sample_code(prefix: str, collection_date: date) -> str:
    prefix = prefix or "SMP"
    if not isinstance(collection_date, date):
        collection_date = datetime.utcnow().date()
    timestamp = collection_date.strftime("%Y%m%d")
    random_part = datetime.utcnow().strftime("%H%M%S")
    return f"{prefix}-{timestamp}-{random_part}"


def get_client_ip(flask_request: Request | None = None) -> str:
    ctx_request = flask_request or request
    if not ctx_request:
        return "unknown"
    forwarded_for = ctx_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return ctx_request.remote_addr or "unknown"


def format_number(value: float | None, precision: int = 2) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{precision}f}"
    except (TypeError, ValueError):
        return str(value)


def format_date_arabic(value: datetime | date | None) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    months = [
        "يناير",
        "فبراير",
        "مارس",
        "أبريل",
        "ماي",
        "يونيو",
        "يوليو",
        "أغسطس",
        "سبتمبر",
        "أكتوبر",
        "نوفمبر",
        "ديسمبر",
    ]
    return f"{value.day} {months[value.month - 1]} {value.year}"


def calculate_uncertainty(values: Iterable[float]) -> float:
    values = [float(v) for v in values if v is not None]
    if not values:
        return 0.0
    mean_value = sum(values) / len(values)
    variance = sum((v - mean_value) ** 2 for v in values) / len(values)
    return round(variance ** 0.5, 4)


def get_user_permissions(user: User) -> list[str]:
    if not user:
        return []
    return user.get_permissions()
