#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jawdati Flask application factory."""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, render_template_string

from config import Config, get_config
from extensions import db, login_manager


def _ensure_directories(app: Flask) -> None:
    paths = {
        "DATA_DIR": Path(app.config["DATA_DIR"]),
        "LOG_DIR": Path(app.config["LOG_DIR"]),
        "UPLOAD_ROOT": Path(app.config.get("UPLOAD_ROOT", app.config.get("UPLOAD_FOLDER", "uploads"))),
        "ARCHIVE_DOCUMENTS_PATH": Path(app.config["ARCHIVE_DOCUMENTS_PATH"]),
        "ARCHIVE_THUMBNAILS_PATH": Path(app.config["ARCHIVE_THUMBNAILS_PATH"]),
        "ARCHIVE_VERSIONS_PATH": Path(app.config["ARCHIVE_VERSIONS_PATH"]),
        "ARCHIVE_TEMP_PATH": Path(app.config["ARCHIVE_TEMP_PATH"]),
        "BACKUP_PATH": Path(app.config["BACKUP_PATH"]),
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    app.config.setdefault("UPLOAD_FOLDER", str(paths["UPLOAD_ROOT"]))


def _configure_logging(app: Flask) -> None:
    logging.basicConfig(
        level=app.config.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.logger = logging.getLogger(app.import_name)


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    config_cls = config_object or get_config()
    app.config.from_object(config_cls)

    _ensure_directories(app)
    _configure_logging(app)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة."
    login_manager.login_message_category = "info"

    from lims.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        if not user_id:
            return None
        return User.query.get(int(user_id))

    from lims.routes.auth import auth_bp
    from lims.routes.dashboard import dashboard_bp
    from lims.routes.samples import samples_bp
    from lims.routes.results import results_bp
    from lims.routes.reports import reports_bp as lims_reports_bp
    from archive import archive_bp
    from reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(samples_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(lims_reports_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        return render_template_string(
            """
            <!DOCTYPE html>
            <html lang="ar" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{{ app_name }}</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <div class="text-center mb-4">
                        <h1 class="fw-bold">مرحباً بك في نظام جودتي</h1>
                        <p class="lead">Jawdati - Laboratory Information Management System</p>
                    </div>
                    <div class="text-center">
                        <a class="btn btn-primary me-2" href="{{ url_for('auth.login') }}">تسجيل الدخول</a>
                        <a class="btn btn-outline-primary" href="{{ url_for('archive.index') }}">الأرشيف</a>
                    </div>
                </div>
            </body>
            </html>
            """,
            app_name=app.config.get("APP_NAME", "Jawdati"),
        )

    with app.app_context():
        if not app.config.get("TESTING") and not app.config.get("SKIP_DB_CREATE"):
            db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
