"""Archive blueprint routes."""
from __future__ import annotations

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from extensions import db
from lims.models.user import UserRole, requires_roles

from .models import Category, Document, DocumentVersion, SearchIndex
from .services.ocr_service import ocr_service_factory
from .services.storage_service import storage_service_factory

archive_bp = Blueprint("archive", __name__, url_prefix="/archive")


def _require_owner_or_roles(document: Document, roles: tuple[UserRole, ...]) -> None:
    if document.uploaded_by_id == current_user.id:
        return
    if not current_user.has_any_role(roles):
        abort(403)


@archive_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("SEARCH_RESULTS_PER_PAGE", 20)
    search = request.args.get("search", "")
    category_id = request.args.get("category", type=int)
    document_type = request.args.get("type", "")

    query = Document.query
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Document.title.ilike(term),
                Document.description.ilike(term),
                Document.ocr_text.ilike(term),
            )
        )
    if category_id:
        query = query.filter(Document.category_id == category_id)
    if document_type:
        query = query.filter(Document.document_type == document_type)

    documents = query.order_by(Document.created_at.desc()).paginate(page=page, per_page=per_page)
    categories = Category.query.order_by(Category.name).all()
    storage_service = storage_service_factory()

    stats = {
        "total_documents": Document.query.count(),
        "total_categories": Category.query.count(),
        "ocr_processed": Document.query.filter(Document.ocr_processed.is_(True)).count(),
        "storage_stats": storage_service.get_storage_stats(),
    }

    return render_template(
        "archive/index.html",
        documents=documents,
        categories=categories,
        stats=stats,
        search=search,
        selected_category=category_id,
        selected_type=document_type,
    )


@archive_bp.route("/upload", methods=["GET", "POST"])
@login_required
@requires_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ANALYST)
def upload():
    storage_service = storage_service_factory()
    ocr_service = ocr_service_factory()

    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("لم يتم اختيار ملف", "error")
            return redirect(request.url)

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        document_type = request.form.get("document_type", "").strip()
        category_id = request.form.get("category_id", type=int)
        tags = request.form.get("tags", "").strip()
        access_level = request.form.get("access_level", "public")
        is_confidential = request.form.get("is_confidential") == "on"
        ocr_language = request.form.get("ocr_language", current_app.config.get("OCR_DEFAULT_LANGUAGE"))

        if not title:
            flash("عنوان المستند مطلوب", "error")
            return redirect(request.url)
        if not document_type:
            flash("نوع المستند مطلوب", "error")
            return redirect(request.url)

        document = Document(
            title=title,
            description=description,
            document_type=document_type,
            category_id=category_id,
            tags=tags,
            access_level=access_level,
            is_confidential=is_confidential,
            ocr_language=ocr_language,
            uploaded_by_id=current_user.id,
        )
        db.session.add(document)
        db.session.flush()

        try:
            stored = storage_service.save_upload(file, document.id)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return redirect(request.url)

        document.file_name = stored.original_name
        document.file_path = stored.storage_path
        document.file_size = stored.size
        document.mime_type = stored.mime_type

        if current_app.config.get("OCR_ENABLED", True):
            full_path = storage_service.get_full_path(stored.storage_path)
            text, confidence = ocr_service.extract_text(Path(full_path), language=ocr_language)
            if text:
                document.ocr_text = text
                document.ocr_confidence = confidence
                document.ocr_processed = True
                search_index = SearchIndex(
                    document_id=document.id,
                    content=f"{title} {description} {text}",
                    keywords=tags,
                )
                db.session.add(search_index)

        db.session.commit()
        flash("تم رفع المستند بنجاح", "success")
        return redirect(url_for("archive.view", id=document.id))

    categories = Category.query.order_by(Category.name).all()
    return render_template("archive/upload.html", categories=categories)


@archive_bp.route("/document/<int:id>")
@login_required
def view(id: int):
    document = Document.query.get_or_404(id)
    if document.is_confidential:
        _require_owner_or_roles(document, (UserRole.ADMIN, UserRole.SUPERVISOR))

    versions = DocumentVersion.query.filter_by(document_id=id).order_by(DocumentVersion.created_at.desc()).all()
    return render_template("archive/view.html", document=document, versions=versions)


@archive_bp.route("/document/<int:id>/download")
@login_required
def download(id: int):
    document = Document.query.get_or_404(id)
    if document.is_confidential:
        _require_owner_or_roles(document, (UserRole.ADMIN, UserRole.SUPERVISOR))

    storage_service = storage_service_factory()
    path = storage_service.get_full_path(document.file_path)
    return send_file(path, as_attachment=True, download_name=document.file_name)


@archive_bp.route("/document/<int:id>/edit", methods=["GET", "POST"])
@login_required
@requires_roles(UserRole.ADMIN, UserRole.SUPERVISOR)
def edit(id: int):
    document = Document.query.get_or_404(id)
    if request.method == "POST":
        document.title = request.form.get("title", document.title).strip()
        document.description = request.form.get("description", document.description).strip()
        document.document_type = request.form.get("document_type", document.document_type).strip()
        document.category_id = request.form.get("category_id", type=int)
        document.tags = request.form.get("tags", document.tags).strip()
        document.access_level = request.form.get("access_level", document.access_level)
        document.is_confidential = request.form.get("is_confidential") == "on"
        db.session.commit()
        flash("تم تحديث المستند", "success")
        return redirect(url_for("archive.view", id=document.id))

    categories = Category.query.order_by(Category.name).all()
    return render_template("archive/edit.html", document=document, categories=categories)


@archive_bp.route("/document/<int:id>/delete", methods=["POST"])
@login_required
@requires_roles(UserRole.ADMIN)
def delete(id: int):
    document = Document.query.get_or_404(id)
    db.session.delete(document)
    db.session.commit()
    flash("تم حذف المستند", "info")
    return redirect(url_for("archive.index"))
