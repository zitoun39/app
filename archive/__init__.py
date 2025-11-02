# Archive Module - وحدة الأرشيف الإلكتروني
# Electronic Document Archive System with OCR

__version__ = '1.0.0'
__author__ = 'ADE - الجزائرية للمياه'

from flask import Blueprint

# إنشاء البلوبرينت للأرشيف الإلكتروني
archive_bp = Blueprint('archive', __name__, 
                      template_folder='templates',
                      static_folder='static',
                      url_prefix='/archive')

# استيراد المسارات
from . import routes

# استيراد النماذج والوحدات
from .models import Document, Category, DocumentVersion, SearchIndex
from .ocr import OCRProcessor
from .storage import FileStorage

__all__ = [
    'archive_bp',
    'Document', 'Category', 'DocumentVersion', 'SearchIndex',
    'OCRProcessor',
    'FileStorage'
]