"""Minimal PDF generator stub."""
from __future__ import annotations

from pathlib import Path


def create_pdf_report(content: str, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
