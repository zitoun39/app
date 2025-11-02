from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Document(Base):
    """نموذج المستند الإلكتروني"""
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, comment='عنوان المستند')
    description = Column(Text, comment='وصف المستند')
    document_type = Column(String(50), nullable=False, comment='نوع المستند')
    file_name = Column(String(255), nullable=False, comment='اسم الملف')
    file_path = Column(String(500), nullable=False, comment='مسار الملف')
    file_size = Column(Integer, comment='حجم الملف بالبايت')
    mime_type = Column(String(100), comment='نوع MIME للملف')
    
    # معلومات OCR
    ocr_text = Column(Text, comment='النص المستخرج بواسطة OCR')
    ocr_confidence = Column(Integer, comment='مستوى الثقة في OCR (0-100)')
    ocr_processed = Column(Boolean, default=False, comment='هل تم معالجة OCR')
    ocr_language = Column(String(10), default='ara', comment='لغة OCR')
    
    # معلومات التصنيف
    category_id = Column(Integer, ForeignKey('categories.id'), comment='معرف الفئة')
    tags = Column(String(500), comment='العلامات (مفصولة بفواصل)')
    
    # معلومات الأمان
    access_level = Column(String(20), default='public', comment='مستوى الوصول')
    is_confidential = Column(Boolean, default=False, comment='هل المستند سري')
    
    # معلومات التتبع
    uploaded_by = Column(Integer, ForeignKey('users.id'), comment='معرف المستخدم الذي رفع الملف')
    created_at = Column(DateTime, default=datetime.utcnow, comment='تاريخ الإنشاء')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='تاريخ التحديث')
    
    # العلاقات
    category = relationship('Category', back_populates='documents')
    versions = relationship('DocumentVersion', back_populates='document', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Document {self.title}>'

class Category(Base):
    """نموذج فئات المستندات"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, comment='اسم الفئة')
    description = Column(Text, comment='وصف الفئة')
    parent_id = Column(Integer, ForeignKey('categories.id'), comment='معرف الفئة الأب')
    color = Column(String(7), default='#007bff', comment='لون الفئة')
    icon = Column(String(50), comment='أيقونة الفئة')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='تاريخ الإنشاء')
    
    # العلاقات
    documents = relationship('Document', back_populates='category')
    children = relationship('Category', backref='parent', remote_side=[id])
    
    def __repr__(self):
        return f'<Category {self.name}>'

class DocumentVersion(Base):
    """نموذج إصدارات المستند"""
    __tablename__ = 'document_versions'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, comment='معرف المستند')
    version_number = Column(String(20), nullable=False, comment='رقم الإصدار')
    file_path = Column(String(500), nullable=False, comment='مسار ملف الإصدار')
    file_size = Column(Integer, comment='حجم الملف')
    
    # معلومات التغيير
    change_description = Column(Text, comment='وصف التغيير')
    uploaded_by = Column(Integer, ForeignKey('users.id'), comment='معرف المستخدم')
    created_at = Column(DateTime, default=datetime.utcnow, comment='تاريخ الإنشاء')
    
    # العلاقات
    document = relationship('Document', back_populates='versions')
    
    def __repr__(self):
        return f'<DocumentVersion {self.document_id}-{self.version_number}>'

class SearchIndex(Base):
    """فهرس البحث للمستندات"""
    __tablename__ = 'search_index'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, comment='معرف المستند')
    content = Column(Text, nullable=False, comment='المحتوى المفهرس')
    keywords = Column(Text, comment='الكلمات المفتاحية')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='تاريخ الفهرسة')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='تاريخ التحديث')
    
    def __repr__(self):
        return f'<SearchIndex {self.document_id}>'