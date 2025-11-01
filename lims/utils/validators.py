"""Validation helpers for forms and API payloads."""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping


def _response(valid: bool, message: str = "") -> dict[str, Any]:
    return {"valid": valid, "message": message}


def validate_sample_data(data: Mapping[str, Any]) -> dict[str, Any]:
    required_fields = ["sample_type_id", "collection_date", "location_name"]
    for field in required_fields:
        if not data.get(field):
            return _response(False, f"الحقل {field} مطلوب")
    collection_date = data.get("collection_date")
    if isinstance(collection_date, str):
        try:
            collection_date = date.fromisoformat(collection_date)
        except ValueError:
            return _response(False, "صيغة التاريخ غير صحيحة")
    if collection_date and collection_date > date.today():
        return _response(False, "تاريخ الجمع لا يمكن أن يكون في المستقبل")
    return _response(True)


def validate_result_value(value: Any, min_limit: float | None = None, max_limit: float | None = None) -> dict[str, Any]:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return _response(False, "القيمة يجب أن تكون رقمية")

    if min_limit is not None and numeric_value < min_limit:
        return _response(False, "القيمة أقل من الحد الأدنى")
    if max_limit is not None and numeric_value > max_limit:
        return _response(False, "القيمة أعلى من الحد الأقصى")
    return _response(True)
