# Report Generator - مولد التقارير

from datetime import datetime
import os
from .pdf_generator import generate_sample_report, generate_statistical_report
from lims.models import Sample, Result, Parameter
from app import db

def generate_sample_report_by_id(sample_id):
    """إنشاء تقرير لعينة محددة بواسطة المعرف
    
    Args:
        sample_id: معرف العينة
        
    Returns:
        بيانات PDF أو None إذا لم يتم العثور على العينة
    """
    sample = Sample.query.get(sample_id)
    if not sample:
        return None
        
    # الحصول على نتائج العينة
    results = Result.query.filter_by(sample_id=sample_id).all()
    
    # إنشاء التقرير
    return generate_sample_report(sample, results)

def generate_monthly_statistical_report(year, month):
    """إنشاء تقرير إحصائي شهري
    
    Args:
        year: السنة
        month: الشهر
        
    Returns:
        بيانات PDF
    """
    # تحديد تاريخ البداية والنهاية
    from datetime import datetime, date
    import calendar
    
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # اسم الشهر بالعربية
    arabic_months = {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
        7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    }
    
    month_name = arabic_months.get(month, str(month))
    title = f"التقرير الإحصائي الشهري - {month_name} {year}"
    
    # إنشاء التقرير
    return generate_statistical_report(title, start_date, end_date)

def generate_yearly_statistical_report(year):
    """إنشاء تقرير إحصائي سنوي
    
    Args:
        year: السنة
        
    Returns:
        بيانات PDF
    """
    # تحديد تاريخ البداية والنهاية
    from datetime import datetime, date
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    title = f"التقرير الإحصائي السنوي - {year}"
    
    # إنشاء التقرير
    return generate_statistical_report(title, start_date, end_date)

def generate_compliance_report(start_date, end_date, parameter_id=None):
    """إنشاء تقرير المطابقة
    
    Args:
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
        parameter_id: معرف المعيار (اختياري)
        
    Returns:
        بيانات PDF
    """
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from .pdf_generator import reshape_arabic, generate_pdf_report
    
    # تحضير المحتوى
    content = []
    
    # معلومات الفترة
    period_info = [
        [reshape_arabic("تاريخ البداية"), reshape_arabic(start_date.strftime("%Y-%m-%d"))],
        [reshape_arabic("تاريخ النهاية"), reshape_arabic(end_date.strftime("%Y-%m-%d"))],
    ]
    
    period_table = Table(period_info, colWidths=[150, 300])
    period_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Arabic' if 'Arabic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    content.append(period_table)
    content.append(Spacer(1, 24))
    
    # تحديد المعايير للتقرير
    if parameter_id:
        parameters = [Parameter.query.get(parameter_id)]
        if not parameters[0]:
            return None
    else:
        parameters = Parameter.query.all()
    
    # إنشاء جدول المطابقة
    content.append(Paragraph(reshape_arabic("تقرير المطابقة للمعايير"), getSampleStyleSheet()['Heading2']))
    
    compliance_data = [
        [reshape_arabic("المعيار"), reshape_arabic("الفئة"), reshape_arabic("إجمالي القياسات"), 
         reshape_arabic("القياسات المطابقة"), reshape_arabic("القياسات غير المطابقة"), reshape_arabic("نسبة المطابقة")]
    ]
    
    for param in parameters:
        # الحصول على نتائج هذا المعيار
        total_results = Result.query.join(Sample).filter(
            Sample.collection_date.between(start_date, end_date),
            Result.parameter_id == param.id
        ).count()
        
        conforming_results = Result.query.join(Sample).filter(
            Sample.collection_date.between(start_date, end_date),
            Result.parameter_id == param.id,
            Result.is_conforming == True
        ).count()
        
        non_conforming_results = total_results - conforming_results
        
        conformity_rate = (conforming_results / total_results * 100) if total_results > 0 else 0
        
        compliance_data.append([
            reshape_arabic(param.name),
            reshape_arabic(param.category),
            reshape_arabic(str(total_results)),
            reshape_arabic(str(conforming_results)),
            reshape_arabic(str(non_conforming_results)),
            reshape_arabic(f"{conformity_rate:.1f}%")
        ])
    
    # إضافة صف للإجمالي
    total_all = sum(int(row[2]) for row in compliance_data[1:])
    total_conforming = sum(int(row[3]) for row in compliance_data[1:])
    total_non_conforming = sum(int(row[4]) for row in compliance_data[1:])
    total_rate = (total_conforming / total_all * 100) if total_all > 0 else 0
    
    compliance_data.append([
        reshape_arabic("الإجمالي"),
        reshape_arabic(""),
        reshape_arabic(str(total_all)),
        reshape_arabic(str(total_conforming)),
        reshape_arabic(str(total_non_conforming)),
        reshape_arabic(f"{total_rate:.1f}%")
    ])
    
    compliance_table = Table(compliance_data, colWidths=[80, 80, 80, 80, 80, 80])
    compliance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  # تلوين صف الإجمالي
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Arabic' if 'Arabic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    content.append(compliance_table)
    
    # إنشاء التقرير
    title = "تقرير المطابقة للمعايير"
    if parameter_id:
        param = parameters[0]
        title = f"تقرير المطابقة - {param.name}"
    
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../static/images/logo.png')
    
    return generate_pdf_report(title, content, logo_path)

def generate_quality_report(start_date, end_date):
    """إنشاء تقرير الجودة
    
    Args:
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
        
    Returns:
        بيانات PDF
    """
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from .pdf_generator import reshape_arabic, generate_pdf_report, pdfmetrics
    
    # تحضير المحتوى
    content = []
    
    # معلومات الفترة
    period_info = [
        [reshape_arabic("تاريخ البداية"), reshape_arabic(start_date.strftime("%Y-%m-%d"))],
        [reshape_arabic("تاريخ النهاية"), reshape_arabic(end_date.strftime("%Y-%m-%d"))],
    ]
    
    period_table = Table(period_info, colWidths=[150, 300])
    period_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Arabic' if 'Arabic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    content.append(period_table)
    content.append(Spacer(1, 24))
    
    # إحصائيات الجودة
    content.append(Paragraph(reshape_arabic("مؤشرات الجودة"), getSampleStyleSheet()['Heading2']))
    
    # الحصول على البيانات
    total_samples = Sample.query.filter(Sample.collection_date.between(start_date, end_date)).count()
    
    # تجميع العينات حسب الموقع
    from sqlalchemy import func
    location_stats = db.session.query(
        Sample.location, 
        func.count(Sample.id).label('total'),
        func.sum(case((Sample.is_conforming == True, 1), else_=0)).label('conforming')
    ).filter(
        Sample.collection_date.between(start_date, end_date)
    ).group_by(Sample.location).all()
    
    # إنشاء جدول إحصائيات المواقع
    location_data = [
        [reshape_arabic("الموقع"), reshape_arabic("إجمالي العينات"), 
         reshape_arabic("العينات المطابقة"), reshape_arabic("نسبة المطابقة")]
    ]
    
    for location, total, conforming in location_stats:
        conformity_rate = (conforming / total * 100) if total > 0 else 0
        location_data.append([
            reshape_arabic(location),
            reshape_arabic(str(total)),
            reshape_arabic(str(conforming)),
            reshape_arabic(f"{conformity_rate:.1f}%")
        ])
    
    location_table = Table(location_data, colWidths=[150, 100, 100, 100])
    location_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Arabic' if 'Arabic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    content.append(location_table)
    content.append(Spacer(1, 24))
    
    # تجميع المعايير الأكثر عدم مطابقة
    non_conforming_params = db.session.query(
        Parameter.name,
        Parameter.category,
        func.count(Result.id).label('total_non_conforming')
    ).join(Result, Parameter.id == Result.parameter_id
    ).join(Sample, Result.sample_id == Sample.id
    ).filter(
        Sample.collection_date.between(start_date, end_date),
        Result.is_conforming == False
    ).group_by(Parameter.id
    ).order_by(func.count(Result.id).desc()
    ).limit(10).all()
    
    # إنشاء جدول المعايير الأكثر عدم مطابقة
    content.append(Paragraph(reshape_arabic("المعايير الأكثر عدم مطابقة"), getSampleStyleSheet()['Heading2']))
    
    if non_conforming_params:
        params_data = [
            [reshape_arabic("المعيار"), reshape_arabic("الفئة"), reshape_arabic("عدد حالات عدم المطابقة")]
        ]
        
        for name, category, count in non_conforming_params:
            params_data.append([
                reshape_arabic(name),
                reshape_arabic(category),
                reshape_arabic(str(count))
            ])
        
        params_table = Table(params_data, colWidths=[150, 150, 150])
        params_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Arabic' if 'Arabic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        content.append(params_table)
    else:
        content.append(Paragraph(reshape_arabic("لا توجد معايير غير مطابقة في هذه الفترة"), getSampleStyleSheet()['Normal']))
    
    # إنشاء التقرير
    title = "تقرير الجودة"
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../static/images/logo.png')
    
    return generate_pdf_report(title, content, logo_path)