#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إعدادات التكوين لنظام جودتي
Configuration settings for Jawdati LIMS
"""

import os
from datetime import timedelta

class Config:
    """إعدادات التكوين الأساسية"""
    
    # إعدادات التطبيق الأساسية
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'jawdati-secret-key-2024-ade-algeria'
    
    # إعدادات قاعدة البيانات
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "data", "jawdati.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {'check_same_thread': False} if 'sqlite' in SQLALCHEMY_DATABASE_URI else {}
    }
    
    # إعدادات الجلسة
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # True في الإنتاج مع HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # إعدادات رفع الملفات
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {
        'documents': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
        'images': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'},
        'spreadsheets': {'xls', 'xlsx', 'csv'},
        'archives': {'zip', 'rar', '7z'},
        'all': {'pdf', 'doc', 'docx', 'txt', 'rtf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'xls', 'xlsx', 'csv', 'zip', 'rar', '7z'}
    }
    
    # إعدادات الأرشيف الإلكتروني
    ARCHIVE_STORAGE_PATH = 'archive_storage'
    ARCHIVE_DOCUMENTS_PATH = os.path.join(ARCHIVE_STORAGE_PATH, 'documents')
    ARCHIVE_THUMBNAILS_PATH = os.path.join(ARCHIVE_STORAGE_PATH, 'thumbnails')
    ARCHIVE_VERSIONS_PATH = os.path.join(ARCHIVE_STORAGE_PATH, 'versions')
    ARCHIVE_TEMP_PATH = os.path.join(ARCHIVE_STORAGE_PATH, 'temp')
    
    # إعدادات OCR
    OCR_ENABLED = True
    OCR_LANGUAGES = ['ara', 'eng']  # العربية والإنجليزية
    OCR_DEFAULT_LANGUAGE = 'ara+eng'
    OCR_CONFIDENCE_THRESHOLD = 60
    TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # مسار Tesseract على Windows
    
    # إعدادات البحث والفهرسة
    SEARCH_INDEX_PATH = 'data/search_index'
    SEARCH_RESULTS_PER_PAGE = 20
    SEARCH_EXCERPT_LENGTH = 200
    
    # إعدادات التقارير
    REPORTS_PATH = 'reports'
    REPORT_LOGO_PATH = 'static/images/ade_logo.png'
    REPORT_TEMPLATE_PATH = 'templates/reports'
    
    # إعدادات النسخ الاحتياطي
    BACKUP_PATH = 'backups'
    BACKUP_RETENTION_DAYS = 30
    AUTO_BACKUP_ENABLED = True
    AUTO_BACKUP_INTERVAL = 24  # ساعات
    
    # إعدادات Google Drive (للنسخ الاحتياطي)
    GOOGLE_DRIVE_ENABLED = False
    GOOGLE_DRIVE_CREDENTIALS_FILE = 'credentials/google_drive_credentials.json'
    GOOGLE_DRIVE_BACKUP_FOLDER = 'Jawdati_Backups'
    
    # إعدادات البريد الإلكتروني
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@ade.dz'
    
    # إعدادات السجلات
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'logs/jawdati.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # إعدادات الأمان
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # ساعة واحدة
    
    # إعدادات التخزين المؤقت
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 دقائق
    
    # إعدادات التطبيق المخصصة
    APP_NAME = 'جودتي - Jawdati LIMS'
    APP_VERSION = '1.0.0'
    COMPANY_NAME = 'الجزائرية للمياه - ADE'
    COMPANY_ADDRESS = 'الجزائر العاصمة، الجزائر'
    COMPANY_PHONE = '+213 21 XX XX XX'
    COMPANY_EMAIL = 'contact@ade.dz'
    COMPANY_WEBSITE = 'https://www.ade.dz'
    
    # إعدادات المنطقة الزمنية واللغة
    TIMEZONE = 'Africa/Algiers'
    DEFAULT_LANGUAGE = 'ar'
    SUPPORTED_LANGUAGES = ['ar', 'en', 'fr']
    
    # إعدادات الصفحات
    ITEMS_PER_PAGE = 25
    MAX_SEARCH_RESULTS = 1000
    
    # إعدادات الأداء
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_TIMEOUT = 20
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_MAX_OVERFLOW = 20
    
    # إعدادات التطوير
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 'on']
    TESTING = False
    
    @staticmethod
    def init_app(app):
        """تهيئة التطبيق مع الإعدادات"""
        pass

class DevelopmentConfig(Config):
    """إعدادات بيئة التطوير"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///data/jawdati_dev.db'
    
class TestingConfig(Config):
    """إعدادات بيئة الاختبار"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
class ProductionConfig(Config):
    """إعدادات بيئة الإنتاج"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///data/jawdati_prod.db'
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # إعداد السجلات للإنتاج
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/jawdati.log',
                maxBytes=cls.LOG_MAX_BYTES,
                backupCount=cls.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s %(name)s %(message)s'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('Jawdati LIMS startup')

# تحديد التكوين حسب البيئة
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# الحصول على التكوين الحالي
def get_config():
    """الحصول على تكوين البيئة الحالية"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])