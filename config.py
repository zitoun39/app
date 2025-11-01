#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jawdati configuration module."""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if present
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "on", "yes"}


class Config:
    """Base configuration shared across environments."""

    APP_NAME = "جودتي - Jawdati LIMS"
    APP_VERSION = "1.0.0"

    DATA_DIR = ROOT_DIR / "data"
    LOG_DIR = ROOT_DIR / "logs"
    UPLOAD_ROOT = ROOT_DIR / "uploads"
    ARCHIVE_STORAGE_PATH = ROOT_DIR / "archive_storage"
    BACKUP_PATH = ROOT_DIR / "backups"

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is required. Populate it via environment or .env file.")

    default_db_path = DATA_DIR / "jawdati.db"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI", f"sqlite:///{default_db_path}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {"check_same_thread": False}
        if SQLALCHEMY_DATABASE_URI.startswith("sqlite:")
        else {},
    }

    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_TIMEOUT = 20
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_MAX_OVERFLOW = 20

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _to_bool(os.environ.get("SESSION_COOKIE_SECURE"), default=False)

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 100 * 1024 * 1024))

    ALLOWED_EXTENSIONS = {
        "documents": {"pdf", "doc", "docx", "txt", "rtf"},
        "images": {"png", "jpg", "jpeg", "gif", "bmp", "tiff"},
        "spreadsheets": {"xls", "xlsx", "csv"},
        "archives": {"zip", "rar", "7z"},
    }
    ALLOWED_EXTENSIONS["all"] = set().union(*ALLOWED_EXTENSIONS.values())

    ARCHIVE_DOCUMENTS_PATH = ARCHIVE_STORAGE_PATH / "documents"
    ARCHIVE_THUMBNAILS_PATH = ARCHIVE_STORAGE_PATH / "thumbnails"
    ARCHIVE_VERSIONS_PATH = ARCHIVE_STORAGE_PATH / "versions"
    ARCHIVE_TEMP_PATH = ARCHIVE_STORAGE_PATH / "temp"

    OCR_ENABLED = _to_bool(os.environ.get("OCR_ENABLED"), default=True)
    OCR_LANGUAGES = os.environ.get("OCR_LANGUAGES", "ara,eng").split(",")
    OCR_DEFAULT_LANGUAGE = os.environ.get("OCR_DEFAULT_LANGUAGE", "ara+eng")
    OCR_CONFIDENCE_THRESHOLD = int(os.environ.get("OCR_CONFIDENCE_THRESHOLD", 60))
    TESSERACT_CMD = os.environ.get("TESSERACT_CMD")

    SEARCH_INDEX_PATH = ROOT_DIR / "data" / "search_index"
    SEARCH_RESULTS_PER_PAGE = int(os.environ.get("SEARCH_RESULTS_PER_PAGE", 20))
    SEARCH_EXCERPT_LENGTH = int(os.environ.get("SEARCH_EXCERPT_LENGTH", 200))

    REPORTS_PATH = ROOT_DIR / "reports"
    REPORT_LOGO_PATH = ROOT_DIR / "static" / "images" / "ade_logo.png"
    REPORT_TEMPLATE_PATH = ROOT_DIR / "templates" / "reports"

    BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", 30))
    AUTO_BACKUP_ENABLED = _to_bool(os.environ.get("AUTO_BACKUP_ENABLED"), default=True)
    AUTO_BACKUP_INTERVAL = int(os.environ.get("AUTO_BACKUP_INTERVAL", 24))

    GOOGLE_DRIVE_ENABLED = _to_bool(os.environ.get("GOOGLE_DRIVE_ENABLED"), default=False)
    GOOGLE_DRIVE_CREDENTIALS_FILE = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_FILE")
    GOOGLE_DRIVE_BACKUP_FOLDER = os.environ.get("GOOGLE_DRIVE_BACKUP_FOLDER", "Jawdati_Backups")

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = _to_bool(os.environ.get("MAIL_USE_TLS"), default=True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@ade.dz")

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = LOG_DIR / "jawdati.log"
    LOG_MAX_BYTES = 10 * 1024 * 1024
    LOG_BACKUP_COUNT = 5

    WTF_CSRF_ENABLED = _to_bool(os.environ.get("WTF_CSRF_ENABLED"), default=True)
    WTF_CSRF_TIME_LIMIT = int(os.environ.get("WTF_CSRF_TIME_LIMIT", 3600))

    CACHE_TYPE = os.environ.get("CACHE_TYPE", "simple")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 300))

    TIMEZONE = os.environ.get("TIMEZONE", "Africa/Algiers")
    DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "ar")
    SUPPORTED_LANGUAGES = os.environ.get("SUPPORTED_LANGUAGES", "ar,en,fr").split(",")

    ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", 25))
    MAX_SEARCH_RESULTS = int(os.environ.get("MAX_SEARCH_RESULTS", 1000))

    DEBUG = _to_bool(os.environ.get("FLASK_DEBUG"), default=False)
    TESTING = False

    @staticmethod
    def init_app(app):
        """Hook for application specific initialisation."""
        return None


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URI", f"sqlite:///{Config.DATA_DIR / 'jawdati_dev.db'}"
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URI", "sqlite:///:memory:")
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI", f"sqlite:///{Config.DATA_DIR / 'jawdati_prod.db'}"
    )

    @classmethod
    def init_app(cls, app):
        super().init_app(app)

        import logging
        from logging.handlers import RotatingFileHandler

        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            cls.LOG_FILE, maxBytes=cls.LOG_MAX_BYTES, backupCount=cls.LOG_BACKUP_COUNT, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Jawdati LIMS startup")


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config.get(env, config["default"])
