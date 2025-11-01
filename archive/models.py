"""Archive data models using the shared Flask-SQLAlchemy instance."""
from __future__ import annotations

from datetime import datetime

from extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    color = db.Column(db.String(7), default="#007bff")
    icon = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship("Category", backref=db.backref("parent", remote_side=[id]))
    documents = db.relationship("Document", back_populates="category", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    document_type = db.Column(db.String(50), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))

    ocr_text = db.Column(db.Text)
    ocr_confidence = db.Column(db.Integer)
    ocr_processed = db.Column(db.Boolean, default=False)
    ocr_language = db.Column(db.String(20), default="ara")

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    tags = db.Column(db.String(500))

    access_level = db.Column(db.String(20), default="public")
    is_confidential = db.Column(db.Boolean, default=False)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship("Category", back_populates="documents")
    versions = db.relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.created_at.desc()",
    )
    search_index = db.relationship(
        "SearchIndex", back_populates="document", cascade="all, delete-orphan", uselist=False
    )
    uploaded_by = db.relationship("User", backref=db.backref("archive_documents", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<Document {self.title}>"


class DocumentVersion(db.Model):
    __tablename__ = "document_versions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    version_number = db.Column(db.String(20), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    checksum = db.Column(db.String(128), index=True)
    change_description = db.Column(db.Text)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    document = db.relationship("Document", back_populates="versions")
    uploaded_by = db.relationship("User")

    def __repr__(self) -> str:
        return f"<DocumentVersion {self.document_id}-{self.version_number}>"


class SearchIndex(db.Model):
    __tablename__ = "search_index"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = db.relationship("Document", back_populates="search_index")

    def __repr__(self) -> str:
        return f"<SearchIndex {self.document_id}>"
