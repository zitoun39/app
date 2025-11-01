from __future__ import annotations

from extensions import db
from archive.models import Category, Document, DocumentVersion, SearchIndex
from lims.models.user import User, UserRole


def test_document_crud(app):
    with app.app_context():
        user = User(
            username="tester",
            email="tester@example.com",
            first_name="Test",
            last_name="User",
            role=UserRole.ADMIN,
        )
        user.set_password("secure-password")
        db.session.add(user)
        db.session.flush()

        category = Category(name="General")
        db.session.add(category)
        db.session.commit()

        document = Document(
            title="Test Document",
            description="Description",
            document_type="report",
            category_id=category.id,
            file_name="test.pdf",
            file_path="archive_storage/documents/test.pdf",
            uploaded_by_id=user.id,
        )
        db.session.add(document)
        db.session.commit()

        fetched = Document.query.filter_by(title="Test Document").one()
        assert fetched.category_id == category.id

        version = DocumentVersion(
            document_id=document.id,
            version_number="v1",
            file_path="archive_storage/documents/test_v1.pdf",
        )
        db.session.add(version)
        db.session.commit()

        search_index = SearchIndex(document_id=document.id, content="Test", keywords="sample")
        db.session.add(search_index)
        db.session.commit()

        assert fetched.versions[0].version_number == "v1"
        assert fetched.search_index.keywords == "sample"

        db.session.delete(document)
        db.session.commit()

        assert Document.query.count() == 0
