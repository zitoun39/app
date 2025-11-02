#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
جودتي - نظام إدارة معلومات المختبر والأرشيف الإلكتروني
Jawdati - Laboratory Information Management System & Electronic Archive

شركة الجزائرية للمياه - ADE
تطوير: فريق التطوير التقني
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template, render_template_string, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user

# إنشاء التطبيق
app = Flask(__name__)

# تحميل التكوين
from config import Config
app.config.from_object(Config)

# تهيئة قاعدة البيانات قبل الاستيراد
# Use the shared db instance from models package
from lims.models import db
db.init_app(app)

# استيراد النماذج بعد تهيئة قاعدة البيانات
from lims.models import User

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# تسجيل البلوبرنت الخاص بوحدة التقارير (بعد تهيئة قاعدة البيانات)
try:
    from reports import reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')
except ImportError as e:
    print(f"Warning: Could not import reports blueprint: {e}")
    reports_bp = None

# تسجيل البلوبرنت الخاص بلوحة التحكم (بعد تهيئة قاعدة البيانات)
try:
    from lims.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
except ImportError as e:
    print(f"Warning: Could not import dashboard blueprint: {e}")
    dashboard_bp = None

# تهيئة نظام المصادقة
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة.'
login_manager.login_message_category = 'info'

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# إنشاء مجلدات ضرورية
required_dirs = [
    'uploads', 'archive_storage', 'archive_storage/documents',
    'archive_storage/thumbnails', 'archive_storage/versions',
    'archive_storage/temp', 'backups', 'logs', 'static/uploads', 'data'
]

for directory in required_dirs:
    os.makedirs(directory, exist_ok=True)

# تحميل المستخدم للمصادقة (يستخدم الآن النموذج من lims.models)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# الصفحة الرئيسية
@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ app_name }}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .welcome-container {
                padding: 4rem 0;
                color: white;
                text-align: center;
            }
            .logo {
                font-size: 4rem;
                margin-bottom: 2rem;
            }
            .welcome-card {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 3rem;
                margin: 2rem auto;
                max-width: 800px;
                border: 1px solid rgba(255,255,255,0.2);
            }
            .feature-card {
                background: rgba(255,255,255,0.05);
                border-radius: 15px;
                padding: 2rem;
                margin: 1rem;
                border: 1px solid rgba(255,255,255,0.1);
                transition: transform 0.3s ease;
            }
            .feature-card:hover {
                transform: translateY(-5px);
                background: rgba(255,255,255,0.1);
            }
            .btn-primary {
                background: rgba(255,255,255,0.2);
                border: 2px solid rgba(255,255,255,0.3);
                color: white;
                padding: 12px 30px;
                font-size: 1.1rem;
                border-radius: 50px;
                transition: all 0.3s ease;
            }
            .btn-primary:hover {
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.5);
                color: white;
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="container welcome-container">
            <div class="logo">
                <i class="fas fa-flask"></i>
            </div>
            <div class="welcome-card">
                <h1 class="display-4 mb-4">مرحباً بك في نظام جودتي</h1>
                <h2 class="h4 mb-4">Jawdati - Laboratory Information Management System</h2>
                <p class="lead mb-4">
                    نظام إدارة معلومات المختبر والأرشيف الإلكتروني
                    <br>
                    الجزائرية للمياه - ADE
                </p>
                
                <div class="row mt-5">
                    <div class="col-md-4">
                        <div class="feature-card">
                            <i class="fas fa-vial fa-2x mb-3"></i>
                            <h5>إدارة العينات</h5>
                            <p>تتبع وإدارة عينات المياه والتحاليل</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="feature-card">
                            <i class="fas fa-file-alt fa-2x mb-3"></i>
                            <h5>الأرشيف الإلكتروني</h5>
                            <p>حفظ وتنظيم الوثائق مع OCR</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="feature-card">
                            <i class="fas fa-chart-bar fa-2x mb-3"></i>
                            <h5>التقارير</h5>
                            <p>إنتاج التقارير والإحصائيات</p>
                        </div>
                    </div>
                </div>
                
                <div class="mt-5">
                    <a href="/login" class="btn btn-primary btn-lg me-3">
                        <i class="fas fa-sign-in-alt me-2"></i>
                        تسجيل الدخول
                    </a>
                    <a href="/status" class="btn btn-primary btn-lg">
                        <i class="fas fa-info-circle me-2"></i>
                        حالة النظام
                    </a>
                </div>
            </div>
            
            <div class="mt-4">
                <small class="opacity-75">
                    <i class="fas fa-building me-1"></i>
                    {{ company_name }} - الإصدار {{ app_version }}
                </small>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

# صفحة تسجيل الدخول
@app.route('/login')
def login():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>تسجيل الدخول - {{ app_name }}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .login-card {
                background: rgba(255,255,255,0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 3rem;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            .form-control {
                border-radius: 10px;
                padding: 12px 15px;
                border: 2px solid #e9ecef;
            }
            .form-control:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
            }
            .btn-login {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-weight: 600;
                width: 100%;
            }
        </style>
    </head>
    <body>
        <div class="login-card">
            <div class="text-center mb-4">
                <i class="fas fa-flask fa-3x text-primary mb-3"></i>
                <h3>تسجيل الدخول</h3>
                <p class="text-muted">نظام جودتي - Jawdati LIMS</p>
            </div>
            
            <form>
                <div class="mb-3">
                    <label class="form-label">اسم المستخدم</label>
                    <input type="text" class="form-control" value="admin" readonly>
                </div>
                <div class="mb-3">
                    <label class="form-label">كلمة المرور</label>
                    <input type="password" class="form-control" value="admin123" readonly>
                </div>
                <div class="mb-3">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>بيانات الدخول الافتراضية:</strong><br>
                        المستخدم: admin<br>
                        كلمة المرور: admin123
                    </div>
                </div>
                <button type="button" class="btn btn-login text-white" onclick="alert('سيتم تفعيل تسجيل الدخول قريباً')">
                    <i class="fas fa-sign-in-alt me-2"></i>
                    دخول
                </button>
            </form>
            
            <div class="text-center mt-4">
                <a href="/" class="text-decoration-none">
                    <i class="fas fa-arrow-right me-1"></i>
                    العودة للصفحة الرئيسية
                </a>
            </div>
        </div>
    </body>
    </html>
    """)

# صفحة حالة النظام
@app.route('/status')
def status():
    # استيراد معالج OCR للتحقق من حالته
    from archive.ocr import ocr_processor
    
    # التحقق من حالة OCR
    ocr_status = ocr_processor.get_status()
    ocr_module_status = 'installed' if ocr_processor.is_available() else 'installed (needs Tesseract)'
    
    # تحضير بيانات الحالة
    status_data = {
        'status': 'running',
        'app_name': 'جودتي - Jawdati LIMS',
        'version': '1.0.0',
        'company': 'الجزائرية للمياه - ADE',
        'database': 'connected' if db else 'disconnected',
        'timestamp': datetime.now().isoformat(),
        'modules': {
            'lims': 'installed',
            'archive': 'installed',
            'ocr': ocr_module_status,
            'reports': 'installed'
        },
        'ocr_details': ocr_status
    }
    
    # التحقق من نوع الطلب (API أو صفحة ويب)
    if request.headers.get('Accept') == 'application/json':
        return jsonify(status_data)
    
    # عرض صفحة HTML
    return render_template_string('''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>حالة النظام - جودتي</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f8f9fa;
            }
            .status-card {
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
            }
            .status-header {
                background-color: #0d6efd;
                color: white;
                border-radius: 10px 10px 0 0;
                padding: 15px;
            }
            .status-body {
                padding: 20px;
            }
            .module-status {
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: bold;
            }
            .status-installed {
                background-color: #d1e7dd;
                color: #0f5132;
            }
            .status-pending {
                background-color: #fff3cd;
                color: #856404;
            }
            .status-error {
                background-color: #f8d7da;
                color: #842029;
            }
        </style>
    </head>
    <body>
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <div class="card status-card">
                        <div class="status-header text-center">
                            <h2><i class="fas fa-server me-2"></i>حالة النظام</h2>
                            <p class="mb-0">{{ status_data.app_name }} - الإصدار {{ status_data.version }}</p>
                        </div>
                        <div class="status-body">
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <h5><i class="fas fa-info-circle me-2"></i>معلومات النظام</h5>
                                    <ul class="list-group">
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            الشركة
                                            <span>{{ status_data.company }}</span>
                                        </li>
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            حالة النظام
                                            <span class="badge bg-success">{{ status_data.status }}</span>
                                        </li>
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            قاعدة البيانات
                                            <span class="badge {% if status_data.database == 'connected' %}bg-success{% else %}bg-danger{% endif %}">{{ status_data.database }}</span>
                                        </li>
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            التاريخ والوقت
                                            <span>{{ status_data.timestamp.split('T')[0] }} {{ status_data.timestamp.split('T')[1].split('.')[0] }}</span>
                                        </li>
                                    </ul>
                                </div>
                                <div class="col-md-6">
                                    <h5><i class="fas fa-puzzle-piece me-2"></i>الوحدات</h5>
                                    <ul class="list-group">
                                        {% for module, status in status_data.modules.items() %}
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            {{ module }}
                                            <span class="module-status {% if 'installed' in status %}status-installed{% elif 'pending' in status %}status-pending{% else %}status-error{% endif %}">
                                                {{ status }}
                                            </span>
                                        </li>
                                        {% endfor %}
                                    </ul>
                                </div>
                            </div>
                            
                            {% if not status_data.ocr_details.available %}
                            <div class="alert alert-warning" role="alert">
                                <h5><i class="fas fa-exclamation-triangle me-2"></i>تنبيه OCR</h5>
                                <p>{{ status_data.ocr_details.message }}</p>
                                <p>اللغات المدعومة:</p>
                                <ul>
                                    {% for code, lang in status_data.ocr_details.supported_languages.items() %}
                                    <li>{{ lang }} ({{ code }})</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}
                            
                            <div class="text-center mt-4">
                                <a href="/" class="btn btn-primary">
                                    <i class="fas fa-home me-2"></i>العودة للصفحة الرئيسية
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''', status_data=status_data)

# معالج الأخطاء
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# متغيرات القوالب العامة
@app.context_processor
def inject_template_vars():
    return {
        'app_name': 'جودتي - Jawdati',
        'app_version': '1.0.0',
        'company_name': 'الجزائرية للمياه - ADE',
        'current_year': datetime.now().year,
        'current_user': current_user
    }

# فلاتر القوالب المخصصة
@app.template_filter('datetime')
def datetime_filter(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ''
    return value.strftime(format)

@app.template_filter('filesize')
def filesize_filter(value):
    """تحويل حجم الملف إلى وحدة مناسبة"""
    if value is None:
        return '0 B'
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"

# تهيئة قاعدة البيانات
def init_database():
    """تهيئة قاعدة البيانات مع البيانات الأساسية"""
    with app.app_context():
        try:
            # إنشاء الجداول
            db.create_all()
            
            # إنشاء مستخدم إداري افتراضي
            from lims.models import User, UserRole
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@ade.dz',
                    password='admin123',
                    first_name='مدير',
                    last_name='النظام',
                    role=UserRole.ADMIN
                )
                admin_user.is_active = True
                db.session.add(admin_user)
                db.session.commit()
                print("✅ تم إنشاء المستخدم الإداري بنجاح")
            
            print("✅ تم تهيئة قاعدة البيانات بنجاح")
            return True
        except Exception as e:
            print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
            return False

if __name__ == '__main__':
    # تهيئة قاعدة البيانات عند التشغيل لأول مرة
    print("🔧 تهيئة قاعدة البيانات...")
    if init_database():
        print("="*60)
        print("🚀 تشغيل نظام جودتي - Jawdati LIMS")
        print("🏢 الجزائرية للمياه - ADE")
        print("🌐 الرابط: http://localhost:5000")
        print("👤 المستخدم: admin")
        print("🔑 كلمة المرور: admin123")
        print("📊 حالة النظام: http://localhost:5000/status")
        print("="*60)
        
        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            threaded=True
        )
    else:
        print("❌ فشل في تهيئة قاعدة البيانات. يرجى التحقق من الإعدادات.")