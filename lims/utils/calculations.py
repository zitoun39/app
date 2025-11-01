"""Domain specific calculations placeholders."""
from __future__ import annotations

from typing import Any, Iterable


def calculate_parameter_value(raw_value: float, dilution_factor: float = 1.0) -> float:
    try:
        return float(raw_value) * float(dilution_factor)
    except (TypeError, ValueError):
        raise ValueError("Invalid numeric values for calculation")


def check_conformity(value: float, min_limit: float | None, max_limit: float | None) -> dict[str, Any]:
    status = "conforming"
    if min_limit is not None and value < min_limit:
        status = "below"
    if max_limit is not None and value > max_limit:
        status = "above"
    return {"status": status, "value": value, "min_limit": min_limit, "max_limit": max_limit}
