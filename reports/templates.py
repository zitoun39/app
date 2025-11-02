# Report Templates - قوالب التقارير

import os
import shutil
from datetime import datetime

# مسارات القوالب
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'archive')

# إنشاء المجلدات إذا لم تكن موجودة
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def get_default_header():
    """الحصول على محتوى الترويسة الافتراضية"""
    return """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <style>
        .header {
            text-align: center;
            padding: 10px;
            border-bottom: 1px solid #ccc;
        }
        .logo {
            max-height: 80px;
        }
        .company-name {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        .report-title {
            font-size: 18px;
            margin: 5px 0;
        }
        .report-date {
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="../static/images/logo.png" alt="شعار الشركة" class="logo">
        <div class="company-name">الجزائرية للمياه - ADE</div>
        <div class="report-title">{{report_title}}</div>
        <div class="report-date">تاريخ التقرير: {{report_date}}</div>
    </div>
"""

def get_default_footer():
    """الحصول على محتوى التذييل الافتراضي"""
    return """
    <div class="footer">
        <p>جودتي - نظام إدارة المختبر - الجزائرية للمياه</p>
        <p>صفحة {{page_number}} من {{total_pages}}</p>
    </div>
</body>
</html>
"""

def get_default_styles():
    """الحصول على الأنماط الافتراضية"""
    return """
/* أنماط عامة */
body {
    font-family: 'Arial', 'Tahoma', sans-serif;
    margin: 0;
    padding: 20px;
    direction: rtl;
    text-align: right;
}

/* أنماط الجداول */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: center;
}

th {
    background-color: #f2f2f2;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

/* أنماط العناوين */
h1, h2, h3 {
    color: #333;
    margin-top: 20px;
}

h1 {
    font-size: 24px;
    border-bottom: 2px solid #333;
    padding-bottom: 5px;
}

h2 {
    font-size: 20px;
}

h3 {
    font-size: 16px;
}

/* أنماط التذييل */
.footer {
    text-align: center;
    margin-top: 30px;
    padding-top: 10px;
    border-top: 1px solid #ccc;
    font-size: 12px;
    color: #666;
}

/* أنماط للبيانات غير المطابقة */
.non-conforming {
    background-color: #ffdddd;
    color: #cc0000;
}

/* أنماط للبيانات المطابقة */
.conforming {
    background-color: #ddffdd;
    color: #006600;
}
"""

def initialize_default_templates():
    """إنشاء ملفات القوالب الافتراضية إذا لم تكن موجودة"""
    # إنشاء ملف الترويسة
    header_path = os.path.join(TEMPLATES_DIR, 'header.html')
    if not os.path.exists(header_path):
        with open(header_path, 'w', encoding='utf-8') as f:
            f.write(get_default_header())
    
    # إنشاء ملف التذييل
    footer_path = os.path.join(TEMPLATES_DIR, 'footer.html')
    if not os.path.exists(footer_path):
        with open(footer_path, 'w', encoding='utf-8') as f:
            f.write(get_default_footer())
    
    # إنشاء ملف الأنماط
    styles_path = os.path.join(TEMPLATES_DIR, 'styles.css')
    if not os.path.exists(styles_path):
        with open(styles_path, 'w', encoding='utf-8') as f:
            f.write(get_default_styles())

def get_header_content():
    """الحصول على محتوى ملف الترويسة"""
    header_path = os.path.join(TEMPLATES_DIR, 'header.html')
    if os.path.exists(header_path):
        with open(header_path, 'r', encoding='utf-8') as f:
            return f.read()
    return get_default_header()

def get_footer_content():
    """الحصول على محتوى ملف التذييل"""
    footer_path = os.path.join(TEMPLATES_DIR, 'footer.html')
    if os.path.exists(footer_path):
        with open(footer_path, 'r', encoding='utf-8') as f:
            return f.read()
    return get_default_footer()

def get_styles_content():
    """الحصول على محتوى ملف الأنماط"""
    styles_path = os.path.join(TEMPLATES_DIR, 'styles.css')
    if os.path.exists(styles_path):
        with open(styles_path, 'r', encoding='utf-8') as f:
            return f.read()
    return get_default_styles()

def update_header(content):
    """تحديث محتوى ملف الترويسة"""
    header_path = os.path.join(TEMPLATES_DIR, 'header.html')
    with open(header_path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_footer(content):
    """تحديث محتوى ملف التذييل"""
    footer_path = os.path.join(TEMPLATES_DIR, 'footer.html')
    with open(footer_path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_styles(content):
    """تحديث محتوى ملف الأنماط"""
    styles_path = os.path.join(TEMPLATES_DIR, 'styles.css')
    with open(styles_path, 'w', encoding='utf-8') as f:
        f.write(content)

def archive_report(report_data, report_type, report_id):
    """أرشفة تقرير
    
    Args:
        report_data: بيانات التقرير (PDF)
        report_type: نوع التقرير (sample, statistical, compliance, quality)
        report_id: معرف التقرير
        
    Returns:
        مسار الملف المؤرشف
    """
    # إنشاء مجلد للنوع إذا لم يكن موجودًا
    type_dir = os.path.join(ARCHIVE_DIR, report_type)
    os.makedirs(type_dir, exist_ok=True)
    
    # إنشاء مجلد للسنة والشهر
    now = datetime.now()
    year_dir = os.path.join(type_dir, str(now.year))
    month_dir = os.path.join(year_dir, f"{now.month:02d}")
    os.makedirs(month_dir, exist_ok=True)
    
    # إنشاء اسم الملف
    filename = f"{report_type}_{report_id}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = os.path.join(month_dir, filename)
    
    # حفظ الملف
    with open(file_path, 'wb') as f:
        f.write(report_data)
    
    return file_path

def get_archived_reports(report_type=None, year=None, month=None):
    """الحصول على قائمة التقارير المؤرشفة
    
    Args:
        report_type: نوع التقرير (اختياري)
        year: السنة (اختياري)
        month: الشهر (اختياري)
        
    Returns:
        قائمة بمسارات التقارير المؤرشفة
    """
    reports = []
    
    # تحديد المجلد الأساسي للبحث
    base_dir = ARCHIVE_DIR
    if report_type:
        base_dir = os.path.join(base_dir, report_type)
        if not os.path.exists(base_dir):
            return reports
    
    if year:
        base_dir = os.path.join(base_dir, str(year))
        if not os.path.exists(base_dir):
            return reports
    
    if month:
        base_dir = os.path.join(base_dir, f"{month:02d}")
        if not os.path.exists(base_dir):
            return reports
    
    # البحث عن الملفات
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.pdf'):
                reports.append(os.path.join(root, file))
    
    return sorted(reports, key=os.path.getmtime, reverse=True)

# تهيئة القوالب الافتراضية عند استيراد الوحدة
initialize_default_templates()