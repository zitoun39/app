# Reports Routes - مسارات التقارير

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, desc, asc, func
import os
import json
from io import BytesIO

from lims.models import Sample, Parameter, Result, User

# Import db to avoid circular imports
try:
    from app import db
except ImportError:
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()

from .pdf_generator import generate_pdf_report, generate_sample_report, generate_statistical_report

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    """صفحة التقارير الرئيسية"""
    return render_template('reports/index.html')

@reports_bp.route('/sample/<int:sample_id>')
@login_required
def sample_report(sample_id):
    """تقرير العينة"""
    sample = Sample.query.get_or_404(sample_id)
    
    # الحصول على النتائج مجمعة حسب الفئة
    results = Result.query.filter_by(sample_id=sample_id).join(Parameter).order_by(
        Parameter.category, Parameter.name
    ).all()
    
    # تجميع النتائج حسب الفئة
    results_by_category = {}
    for result in results:
        category = result.parameter.category
        if category not in results_by_category:
            results_by_category[category] = []
        results_by_category[category].append(result)
    
    # حساب إحصائيات المطابقة
    total_results = len([r for r in results if r.value is not None])
    conforming_results = len([r for r in results if r.is_conforming])
    conformity_rate = (conforming_results / total_results * 100) if total_results > 0 else 0
    
    return render_template('reports/sample_report.html', 
                         sample=sample, 
                         results_by_category=results_by_category,
                         conformity_rate=conformity_rate)

@reports_bp.route('/sample/<int:sample_id>/pdf')
@login_required
def sample_report_pdf(sample_id):
    """تقرير العينة بصيغة PDF"""
    sample = Sample.query.get_or_404(sample_id)
    
    # الحصول على النتائج
    results = Result.query.filter_by(sample_id=sample_id).join(Parameter).order_by(
        Parameter.category, Parameter.name
    ).all()
    
    # إنشاء التقرير
    pdf_data = generate_sample_report(sample, results)
    
    # إرسال الملف
    filename = f"Sample_Report_{sample.sample_id}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    return send_file(
        BytesIO(pdf_data),
        download_name=filename,
        as_attachment=True,
        mimetype='application/pdf'
    )

@reports_bp.route('/statistics')
@login_required
def statistics_report():
    """تقرير الإحصائيات"""
    # الحصول على المعاملات
    period = request.args.get('period', 'monthly')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # تحديد نطاق التاريخ
    if period == 'monthly':
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        title = f"تقرير شهر {start_date.strftime('%B %Y')}"
    else:  # yearly
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        title = f"التقرير السنوي {year}"
    
    # إحصائيات العينات
    samples_stats = {
        'total': Sample.query.filter(Sample.collection_date.between(start_date, end_date)).count(),
        'conforming': Sample.query.filter(Sample.collection_date.between(start_date, end_date), Sample.is_conforming == True).count(),
        'non_conforming': Sample.query.filter(Sample.collection_date.between(start_date, end_date), Sample.is_conforming == False).count()
    }
    
    # إحصائيات النتائج
    results_stats = {
        'total': Result.query.join(Sample).filter(Sample.collection_date.between(start_date, end_date)).count(),
        'conforming': Result.query.join(Sample).filter(Sample.collection_date.between(start_date, end_date), Result.is_conforming == True).count(),
        'non_conforming': Result.query.join(Sample).filter(Sample.collection_date.between(start_date, end_date), Result.is_conforming == False).count()
    }
    
    # حساب معدلات المطابقة
    samples_stats['conformity_rate'] = (samples_stats['conforming'] / samples_stats['total'] * 100) if samples_stats['total'] > 0 else 0
    results_stats['conformity_rate'] = (results_stats['conforming'] / results_stats['total'] * 100) if results_stats['total'] > 0 else 0
    
    return render_template('reports/statistics_report.html',
                         title=title,
                         period=period,
                         year=year,
                         month=month,
                         start_date=start_date,
                         end_date=end_date,
                         samples_stats=samples_stats,
                         results_stats=results_stats)

@reports_bp.route('/statistics/pdf')
@login_required
def statistics_report_pdf():
    """تقرير الإحصائيات بصيغة PDF"""
    # الحصول على المعاملات
    period = request.args.get('period', 'monthly')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # تحديد نطاق التاريخ
    if period == 'monthly':
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        title = f"تقرير شهر {start_date.strftime('%B %Y')}"
    else:  # yearly
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        title = f"التقرير السنوي {year}"
    
    # إنشاء التقرير
    pdf_data = generate_statistical_report(title, start_date, end_date)
    
    # إرسال الملف
    filename = f"Statistics_Report_{period}_{start_date.strftime('%Y-%m')}.pdf"
    return send_file(
        BytesIO(pdf_data),
        download_name=filename,
        as_attachment=True,
        mimetype='application/pdf'
    )