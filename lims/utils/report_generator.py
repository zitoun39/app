"""Simple report generation utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def generate_sample_report(sample, output_dir: str | Path) -> Dict[str, Any]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {
        "filename": Path(output_dir) / f"sample-{sample.id}.txt",
        "metadata": {"sample_id": sample.sample_id, "status": sample.status.value},
    }


def generate_statistical_report(*args, **kwargs) -> Dict[str, Any]:
    return {"filename": None, "metadata": {"type": "statistical"}}


def generate_compliance_report(*args, **kwargs) -> Dict[str, Any]:
    return {"filename": None, "metadata": {"type": "compliance"}}
