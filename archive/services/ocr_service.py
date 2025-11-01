"""Wrapper around the OCR processor with configuration defaults."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from flask import current_app

from archive.ocr import OCRProcessor


class OCRService:
    def __init__(self, enabled: bool, default_language: str, tesseract_cmd: str | None):
        self.enabled = enabled
        self.default_language = default_language
        self.processor = OCRProcessor(tesseract_cmd)

    def extract_text(self, file_path: Path, language: str | None = None) -> Tuple[str, int]:
        if not self.enabled or not self.processor.tesseract_available:
            return "", 0
        language = language or self.default_language
        suffix = file_path.suffix.lower()
        if suffix in {".pdf"}:
            return self.processor.extract_text_from_pdf(str(file_path), language)
        return self.processor.extract_text_from_image(str(file_path), language)


def ocr_service_factory() -> OCRService:
    app = current_app
    return OCRService(
        enabled=app.config.get("OCR_ENABLED", True),
        default_language=app.config.get("OCR_DEFAULT_LANGUAGE", "ara+eng"),
        tesseract_cmd=app.config.get("TESSERACT_CMD"),
    )
