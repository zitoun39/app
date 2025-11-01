"""Utilities for encrypting backups before uploading them to cloud storage."""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from cryptography.fernet import Fernet


def generate_key_file(path: str | Path) -> bytes:
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    path.write_bytes(key)
    return key


def load_key(path: str | Path) -> bytes:
    path = Path(path)
    if path.exists():
        return path.read_bytes()
    return generate_key_file(path)


def encrypt_file(source: str | Path, destination: str | Path, key: bytes) -> Path:
    cipher = Fernet(key)
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    data = source_path.read_bytes()
    destination_path.write_bytes(cipher.encrypt(data))
    return destination_path


def decrypt_file(source: str | Path, destination: str | Path, key: bytes) -> Path:
    cipher = Fernet(key)
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    encrypted_data = source_path.read_bytes()
    destination_path.write_bytes(cipher.decrypt(encrypted_data))
    return destination_path
