from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from config import TestingConfig
from extensions import db


@pytest.fixture
def app():
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    os.environ["TEST_DATABASE_URI"] = f"sqlite:///{db_path}"

    application = create_app(TestingConfig)
    application.config.update({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}", "TESTING": True, "SKIP_DB_CREATE": True})

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

    os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
