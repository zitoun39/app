# PDF Generator - مولد ملفات PDF

from datetime import datetime
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# تسجيل الخطوط العربية
try:
    # محاولة تسجيل خط عربي
    arabic_font_path = os.path.join('static', 'fonts', 'arabic', 'NotoSansArabic-Regular.ttf')
    if os.path.exists(arabic_font_path):
        pdfmetrics.registerFont(TTFont('Arabic', arabic_font_path))
    else:
        print("تحذير: لم يتم العثور على الخط العربي")
        # استخدام خط افتراضي
        pdfmetrics.registerFont(TTFont('Arabic', 'Helvetica'))
except Exception as e:
    print(f"خطأ في تسجيل الخط العربي: {e}")

# أنماط النصوص
styles = getSampleStyleSheet()
# نمط للنصوص العربية
arabic_style = ParagraphStyle(
    'Arabic',
    parent=styles['Normal'],
    fontName='Arabic',
    alignment=1,  # وسط
    leading=14,
    fontSize=12
)

def generate_pdf_report(title, content, filename=None):
    """
    إنشاء تقرير PDF عام
    
    Args:
        title: عنوان التقرير
        content: محتوى التقرير (قائمة من العناصر)
        filename: اسم الملف (اختياري)
        
    Returns:
        BytesIO: بيانات PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    # إنشاء المستند
    elements = []
    
    # إضافة العنوان
    elements.append(Paragraph(title, arabic_style))
    elements.append(Spacer(1, 20))
    
    # إضافة المحتوى
    for item in content:
        if isinstance(item, str):
            elements.append(Paragraph(item, arabic_style))
            elements.append(Spacer(1, 10))
        else:
            elements.append(item)
    
    # بناء المستند
    doc.build(elements)
    
    # إعادة مؤشر البيانات إلى البداية
    buffer.seek(0)
    
    return buffer

def generate_sample_report(sample, results):
    """
    إنشاء تقرير لعينة محددة
    
    Args:
        sample: كائن العينة
        results: نتائج العينة
        
    Returns:
        BytesIO: بيانات PDF
    """
    # عنوان التقرير
    title = f"تقرير تحليل العينة رقم {sample.id}"
    
    # محتوى التقرير
    content = [
        f"رقم العينة: {sample.id}",
        f"تاريخ الجمع: {sample.collection_date.strftime('%Y-%m-%d')}",
        f"الموقع: {sample.location}",
        f"نوع العينة: {sample.sample_type}",
        f"جمعت بواسطة: {sample.collected_by}",
        Spacer(1, 20),
        "نتائج التحليل:"
    ]
    
    # إنشاء جدول النتائج
    data = [["المعيار", "القيمة", "الوحدة", "الحد المسموح", "المطابقة"]]
    
    for result in results:
        conformity = "مطابق" if result.is_conforming else "غير مطابق"
        data.append([
            result.parameter.name,
            str(result.value) if result.value is not None else "-",
            result.parameter.unit,
            f"{result.parameter.min_value} - {result.parameter.max_value}" if result.parameter.min_value is not None else "-",
            conformity
        ])
    
    # إنشاء الجدول
    table = Table(data, colWidths=[120, 80, 80, 100, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Arabic-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    content.append(table)
    
    # إضافة معلومات إضافية
    content.extend([
        Spacer(1, 20),
        f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d')}",
        "تم إنشاء هذا التقرير بواسطة نظام جودتي - Jawdati LIMS"
    ])
    
    return generate_pdf_report(title, content)

def generate_statistical_report(title, data, period_type, period_value):
    """
    إنشاء تقرير إحصائي
    
    Args:
        title: عنوان التقرير
        data: بيانات التقرير
        period_type: نوع الفترة (شهري/سنوي)
        period_value: قيمة الفترة (الشهر/السنة)
        
    Returns:
        BytesIO: بيانات PDF
    """
    # محتوى التقرير
    content = [
        f"نوع التقرير: تقرير إحصائي {period_type}",
        f"الفترة: {period_value}",
        Spacer(1, 20),
        "ملخص الإحصائيات:"
    ]
    
    # إضافة جدول الإحصائيات
    stats_data = [
        ["البيان", "العدد", "النسبة المئوية"],
        ["إجمالي العينات", str(data['total_samples']), "100%"],
        ["العينات المطابقة", str(data['conforming_samples']), f"{data['conformity_rate']:.1f}%"],
        ["العينات غير المطابقة", str(data['non_conforming_samples']), f"{100 - data['conformity_rate']:.1f}%"],
        ["إجمالي النتائج", str(data['total_results']), "100%"],
        ["النتائج المطابقة", str(data['conforming_results']), f"{data['results_conformity_rate']:.1f}%"],
        ["النتائج غير المطابقة", str(data['non_conforming_results']), f"{100 - data['results_conformity_rate']:.1f}%"]
    ]
    
    # إنشاء الجدول
    stats_table = Table(stats_data, colWidths=[200, 100, 100])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Arabic-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    content.append(stats_table)
    
    # إضافة معلومات إضافية
    content.extend([
        Spacer(1, 20),
        f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d')}",
        "تم إنشاء هذا التقرير بواسطة نظام جودتي - Jawdati LIMS"
    ])
    
    return generate_pdf_report(title, content)