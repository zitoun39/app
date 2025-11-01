"""Secure storage utilities for archive uploads."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Tuple

try:
    import magic  # type: ignore
except ImportError:  # pragma: no cover
    magic = None

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


@dataclass
class StoredFileInfo:
    storage_path: str
    size: int
    checksum: str
    mime_type: str
    original_name: str


class StorageService:
    """Service responsible for validating and storing uploaded documents."""

    def __init__(self, base_path: Path, max_size: int, allowed_extensions: set[str]):
        self.base_path = base_path
        self.max_size = max_size
        self.allowed_extensions = {ext.lower() for ext in allowed_extensions}
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _detect_mime(self, stream: BinaryIO, fallback: str) -> str:
        head = stream.read(4096)
        stream.seek(0)
        if magic:
            try:
                return magic.from_buffer(head, mime=True)  # type: ignore[arg-type]
            except Exception:
                return fallback
        return fallback

    def _ensure_allowed(self, filename: str, mime_type: str, size: int) -> None:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in self.allowed_extensions:
            raise ValueError("نوع الملف غير مدعوم")
        if size > self.max_size:
            raise ValueError("حجم الملف يتجاوز الحد المسموح")
        if mime_type in {"application/octet-stream", "text/plain"} and ext not in {"txt", "pdf"}:
            raise ValueError("تعذر التحقق من نوع الملف")

    def _generate_path(self, filename: str, document_id: int | None) -> Path:
        now = datetime.utcnow()
        fragments = [
            "documents",
            now.strftime("%Y"),
            now.strftime("%m"),
            now.strftime("%d"),
        ]
        directory = self.base_path.joinpath(*fragments)
        directory.mkdir(parents=True, exist_ok=True)
        safe_name = secure_filename(filename)
        token = hashlib.sha1(f"{safe_name}-{now.timestamp()}".encode()).hexdigest()[:12]
        final_name = f"doc_{document_id}_{token}{Path(safe_name).suffix}" if document_id else f"{token}-{safe_name}"
        return directory / final_name

    def save_upload(self, file_storage: FileStorage, document_id: int | None = None) -> StoredFileInfo:
        if not file_storage or not file_storage.filename:
            raise ValueError("لم يتم استلام ملف")

        safe_filename = secure_filename(file_storage.filename)
        if not safe_filename:
            raise ValueError("اسم الملف غير صالح")

        file_storage.stream.seek(0, os.SEEK_END)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)
        mime_type = self._detect_mime(file_storage.stream, file_storage.mimetype or "application/octet-stream")
        self._ensure_allowed(safe_filename, mime_type, size)

        storage_path = self._generate_path(safe_filename, document_id)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        file_storage.save(storage_path)

        checksum = self._checksum(storage_path)
        relative_path = storage_path.relative_to(self.base_path.parent)

        return StoredFileInfo(
            storage_path=str(relative_path).replace(os.sep, "/"),
            size=size,
            checksum=checksum,
            mime_type=mime_type,
            original_name=safe_filename,
        )

    def _checksum(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def get_full_path(self, relative_path: str) -> Path:
        return Path(self.base_path.parent) / relative_path

    def get_storage_stats(self) -> dict[str, int]:
        total_size = 0
        file_count = 0
        for root, _, files in os.walk(self.base_path):
            for filename in files:
                file_count += 1
                total_size += Path(root, filename).stat().st_size
        return {"file_count": file_count, "total_size": total_size}


def storage_service_factory() -> StorageService:
    app = current_app
    allowed = set(app.config.get("ALLOWED_EXTENSIONS", {}).get("all", {"pdf"}))
    return StorageService(
        base_path=Path(app.config["ARCHIVE_DOCUMENTS_PATH"]),
        max_size=int(app.config.get("MAX_CONTENT_LENGTH", 100 * 1024 * 1024)),
        allowed_extensions=allowed,
    )
