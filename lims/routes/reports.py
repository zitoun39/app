# Reports Routes - مسارات التقارير
# Report generation and management

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, desc, asc, func
import json
import os
from io import BytesIO

from ..models import db, Sample, Parameter, Result, ResultStatus, SampleStatus, User, Equipment
from ..utils.report_generator import generate_sample_report, generate_statistical_report, generate_compliance_report
from ..utils.pdf_generator import create_pdf_report
from ..utils.permissions import require_role
from ..utils.helpers import format_date_arabic, format_number

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
    
    # Check if sample is validated
    if sample.status != SampleStatus.VALIDATED:
        flash('العينة غير معتمدة بعد', 'warning')
    
    # Get results grouped by category
    results = Result.query.filter_by(sample_id=sample_id).join(Parameter).order_by(
        Parameter.category, Parameter.display_order
    ).all()
    
    # Group results by category
    results_by_category = {}
    for result in results:
        category = result.parameter.category
        if category not in results_by_category:
            results_by_category[category] = []
        results_by_category[category].append(result)
    
    # Calculate conformity statistics
    total_results = len([r for r in results if r.final_value is not None])
    conforming_results = len([r for r in results if r.conforms_decree and r.final_value is not None])
    conformity_rate = (conforming_results / total_results * 100) if total_results > 0 else 0
    
    report_data = {
        'sample': sample,
        'results_by_category': results_by_category,
        'total_results': total_results,
        'conforming_results': conforming_results,
        'conformity_rate': conformity_rate,
        'generated_at': datetime.now(),
        'generated_by': current_user
    }
    
    return render_template('reports/sample_report.html', **report_data)

@reports_bp.route('/sample/<int:sample_id>/pdf')
@login_required
def sample_report_pdf(sample_id):
    """تقرير العينة بصيغة PDF"""
    sample = Sample.query.get_or_404(sample_id)
    
    try:
        # Generate PDF report
        pdf_buffer = generate_sample_report(sample_id)
        
        # Create filename
        filename = f"تقرير_العينة_{sample.sample_id}_{date.today().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'خطأ في توليد التقرير: {str(e)}', 'error')
        return redirect(url_for('reports.sample_report', sample_id=sample_id))

@reports_bp.route('/statistical', methods=['GET', 'POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def statistical_report():
    """التقرير الإحصائي"""
    if request.method == 'POST':
        try:
            # Get form data
            date_from = datetime.strptime(request.form.get('date_from'), '%Y-%m-%d').date()
            date_to = datetime.strptime(request.form.get('date_to'), '%Y-%m-%d').date()
            parameter_ids = request.form.getlist('parameters')
            sample_types = request.form.getlist('sample_types')
            include_charts = bool(request.form.get('include_charts'))
            
            # Validate date range
            if date_from > date_to:
                flash('تاريخ البداية يجب أن يكون قبل تاريخ النهاية', 'error')
                return render_template('reports/statistical_form.html',
                                     parameters=Parameter.query.filter_by(active=True).all())
            
            # Generate report data
            report_data = generate_statistical_data(
                date_from, date_to, parameter_ids, sample_types
            )
            
            return render_template('reports/statistical_report.html',
                                 report_data=report_data,
                                 date_from=date_from,
                                 date_to=date_to,
                                 include_charts=include_charts)
            
        except ValueError as e:
            flash(f'خطأ في التاريخ: {str(e)}', 'error')
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'error')
    
    # GET request - show form
    parameters = Parameter.query.filter_by(active=True).order_by(Parameter.name_ar).all()
    return render_template('reports/statistical_form.html', parameters=parameters)

@reports_bp.route('/statistical/pdf', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def statistical_report_pdf():
    """التقرير الإحصائي بصيغة PDF"""
    try:
        # Get form data
        date_from = datetime.strptime(request.form.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.strptime(request.form.get('date_to'), '%Y-%m-%d').date()
        parameter_ids = request.form.getlist('parameters')
        sample_types = request.form.getlist('sample_types')
        
        # Generate PDF report
        pdf_buffer = generate_statistical_report(
            date_from, date_to, parameter_ids, sample_types
        )
        
        # Create filename
        filename = f"التقرير_الإحصائي_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'خطأ في توليد التقرير: {str(e)}', 'error')
        return redirect(url_for('reports.statistical_report'))

@reports_bp.route('/compliance', methods=['GET', 'POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def compliance_report():
    """تقرير المطابقة"""
    if request.method == 'POST':
        try:
            # Get form data
            date_from = datetime.strptime(request.form.get('date_from'), '%Y-%m-%d').date()
            date_to = datetime.strptime(request.form.get('date_to'), '%Y-%m-%d').date()
            standard = request.form.get('standard', 'decree')  # decree or who
            location_filter = request.form.get('location', '').strip()
            
            # Generate compliance data
            compliance_data = generate_compliance_data(
                date_from, date_to, standard, location_filter
            )
            
            return render_template('reports/compliance_report.html',
                                 compliance_data=compliance_data,
                                 date_from=date_from,
                                 date_to=date_to,
                                 standard=standard,
                                 location_filter=location_filter)
            
        except ValueError as e:
            flash(f'خطأ في التاريخ: {str(e)}', 'error')
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'error')
    
    # GET request - show form
    return render_template('reports/compliance_form.html')

@reports_bp.route('/compliance/pdf', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def compliance_report_pdf():
    """تقرير المطابقة بصيغة PDF"""
    try:
        # Get form data
        date_from = datetime.strptime(request.form.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.strptime(request.form.get('date_to'), '%Y-%m-%d').date()
        standard = request.form.get('standard', 'decree')
        location_filter = request.form.get('location', '').strip()
        
        # Generate PDF report
        pdf_buffer = generate_compliance_report(
            date_from, date_to, standard, location_filter
        )
        
        # Create filename
        filename = f"تقرير_المطابقة_{standard}_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'خطأ في توليد التقرير: {str(e)}', 'error')
        return redirect(url_for('reports.compliance_report'))

@reports_bp.route('/monthly')
@login_required
@require_role(['ADMIN', 'SUPERVISOR'])
def monthly_report():
    """التقرير الشهري"""
    # Get month and year from query params
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    # Calculate date range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Generate monthly statistics
    monthly_data = generate_monthly_statistics(start_date, end_date)
    
    return render_template('reports/monthly_report.html',
                         monthly_data=monthly_data,
                         month=month,
                         year=year,
                         start_date=start_date,
                         end_date=end_date)

@reports_bp.route('/equipment')
@login_required
@require_role(['ADMIN', 'SUPERVISOR'])
def equipment_report():
    """تقرير الأجهزة"""
    # Get all equipment with their calibration status
    equipment_list = Equipment.query.all()
    
    equipment_data = []
    for equipment in equipment_list:
        # Get latest calibration
        latest_calibration = equipment.calibrations.filter_by(active=True).order_by(
            desc('calibration_date')
        ).first()
        
        # Check calibration status
        calibration_status = 'غير محدد'
        days_until_due = None
        
        if latest_calibration:
            if latest_calibration.next_calibration_date:
                days_until_due = (latest_calibration.next_calibration_date - date.today()).days
                if days_until_due < 0:
                    calibration_status = 'منتهي الصلاحية'
                elif days_until_due <= 30:
                    calibration_status = 'يحتاج معايرة قريباً'
                else:
                    calibration_status = 'صالح'
        
        equipment_data.append({
            'equipment': equipment,
            'latest_calibration': latest_calibration,
            'calibration_status': calibration_status,
            'days_until_due': days_until_due
        })
    
    return render_template('reports/equipment_report.html',
                         equipment_data=equipment_data)

@reports_bp.route('/quality-control')
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def quality_control_report():
    """تقرير مراقبة الجودة"""
    # Get date range
    days = request.args.get('days', 30, type=int)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Get quality control statistics
    qc_data = generate_quality_control_data(start_date, end_date)
    
    return render_template('reports/quality_control_report.html',
                         qc_data=qc_data,
                         start_date=start_date,
                         end_date=end_date,
                         days=days)

@reports_bp.route('/dashboard-data')
@login_required
def dashboard_data():
    """بيانات لوحة التحكم للتقارير"""
    today = date.today()
    month_ago = today - timedelta(days=30)
    
    # Reports generated this month
    reports_generated = 0  # This would be tracked in a reports table
    
    # Most requested parameters
    popular_parameters = db.session.query(
        Parameter.name_ar,
        func.count(Result.id).label('count')
    ).join(Result).filter(
        Result.measurement_date >= month_ago
    ).group_by(Parameter.id).order_by(
        desc('count')
    ).limit(5).all()
    
    # Conformity trends
    conformity_trend = db.session.query(
        func.date(Result.measurement_date).label('date'),
        func.count(Result.id).label('total'),
        func.sum(func.case([(Result.conforms_decree == True, 1)], else_=0)).label('conforming')
    ).filter(
        and_(
            Result.measurement_date >= month_ago,
            Result.status == ResultStatus.VALIDATED
        )
    ).group_by(
        func.date(Result.measurement_date)
    ).order_by('date').all()
    
    return jsonify({
        'reports_generated': reports_generated,
        'popular_parameters': [{'name': name, 'count': count} for name, count in popular_parameters],
        'conformity_trend': [{
            'date': str(date_val),
            'total': total,
            'conforming': conforming,
            'rate': (conforming / total * 100) if total > 0 else 0
        } for date_val, total, conforming in conformity_trend]
    })

# Helper functions
def generate_statistical_data(date_from, date_to, parameter_ids, sample_types):
    """توليد البيانات الإحصائية"""
    # Build query
    query = Result.query.join(Sample).join(Parameter).filter(
        and_(
            Result.measurement_date >= date_from,
            Result.measurement_date <= date_to,
            Result.status == ResultStatus.VALIDATED,
            Result.final_value.isnot(None)
        )
    )
    
    if parameter_ids:
        query = query.filter(Result.parameter_id.in_(parameter_ids))
    
    if sample_types:
        query = query.filter(Sample.sample_type_id.in_(sample_types))
    
    results = query.all()
    
    # Group by parameter
    parameter_stats = {}
    for result in results:
        param_id = result.parameter_id
        if param_id not in parameter_stats:
            parameter_stats[param_id] = {
                'parameter': result.parameter,
                'values': [],
                'conforming': 0,
                'total': 0
            }
        
        parameter_stats[param_id]['values'].append(float(result.final_value))
        parameter_stats[param_id]['total'] += 1
        if result.conforms_decree:
            parameter_stats[param_id]['conforming'] += 1
    
    # Calculate statistics for each parameter
    for param_id, stats in parameter_stats.items():
        values = stats['values']
        if values:
            stats['min'] = min(values)
            stats['max'] = max(values)
            stats['mean'] = sum(values) / len(values)
            stats['median'] = sorted(values)[len(values) // 2]
            stats['conformity_rate'] = (stats['conforming'] / stats['total']) * 100
            
            # Standard deviation
            if len(values) > 1:
                mean = stats['mean']
                variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                stats['std_deviation'] = variance ** 0.5
            else:
                stats['std_deviation'] = 0
    
    return {
        'parameter_stats': parameter_stats,
        'total_samples': len(set(r.sample_id for r in results)),
        'total_results': len(results),
        'date_range': (date_from, date_to)
    }

def generate_compliance_data(date_from, date_to, standard, location_filter):
    """توليد بيانات المطابقة"""
    # Build query
    query = Result.query.join(Sample).join(Parameter).filter(
        and_(
            Result.measurement_date >= date_from,
            Result.measurement_date <= date_to,
            Result.status == ResultStatus.VALIDATED,
            Result.final_value.isnot(None)
        )
    )
    
    if location_filter:
        query = query.filter(Sample.location_name.ilike(f'%{location_filter}%'))
    
    results = query.all()
    
    # Calculate compliance by parameter
    compliance_by_parameter = {}
    for result in results:
        param_id = result.parameter_id
        if param_id not in compliance_by_parameter:
            compliance_by_parameter[param_id] = {
                'parameter': result.parameter,
                'total': 0,
                'conforming': 0,
                'non_conforming_samples': []
            }
        
        compliance_by_parameter[param_id]['total'] += 1
        
        # Check conformity based on standard
        conforms = result.conforms_decree if standard == 'decree' else result.conforms_who
        
        if conforms:
            compliance_by_parameter[param_id]['conforming'] += 1
        else:
            compliance_by_parameter[param_id]['non_conforming_samples'].append({
                'sample': result.sample,
                'value': result.final_value,
                'limit': result.parameter.decree_max if standard == 'decree' else result.parameter.who_max
            })
    
    # Calculate compliance rates
    for param_id, data in compliance_by_parameter.items():
        if data['total'] > 0:
            data['compliance_rate'] = (data['conforming'] / data['total']) * 100
        else:
            data['compliance_rate'] = 0
    
    return {
        'compliance_by_parameter': compliance_by_parameter,
        'standard': standard,
        'total_samples': len(set(r.sample_id for r in results)),
        'date_range': (date_from, date_to)
    }

def generate_monthly_statistics(start_date, end_date):
    """توليد الإحصائيات الشهرية"""
    # Sample statistics
    total_samples = Sample.query.filter(
        and_(
            Sample.created_at >= datetime.combine(start_date, datetime.min.time()),
            Sample.created_at <= datetime.combine(end_date, datetime.max.time())
        )
    ).count()
    
    validated_samples = Sample.query.filter(
        and_(
            Sample.created_at >= datetime.combine(start_date, datetime.min.time()),
            Sample.created_at <= datetime.combine(end_date, datetime.max.time()),
            Sample.status == SampleStatus.VALIDATED
        )
    ).count()
    
    # Result statistics
    total_results = Result.query.filter(
        and_(
            Result.measurement_date >= start_date,
            Result.measurement_date <= end_date
        )
    ).count()
    
    validated_results = Result.query.filter(
        and_(
            Result.measurement_date >= start_date,
            Result.measurement_date <= end_date,
            Result.status == ResultStatus.VALIDATED
        )
    ).count()
    
    # Conformity statistics
    conforming_results = Result.query.filter(
        and_(
            Result.measurement_date >= start_date,
            Result.measurement_date <= end_date,
            Result.status == ResultStatus.VALIDATED,
            Result.conforms_decree == True
        )
    ).count()
    
    return {
        'total_samples': total_samples,
        'validated_samples': validated_samples,
        'total_results': total_results,
        'validated_results': validated_results,
        'conforming_results': conforming_results,
        'sample_validation_rate': (validated_samples / total_samples * 100) if total_samples > 0 else 0,
        'result_validation_rate': (validated_results / total_results * 100) if total_results > 0 else 0,
        'conformity_rate': (conforming_results / validated_results * 100) if validated_results > 0 else 0
    }

def generate_quality_control_data(start_date, end_date):
    """توليد بيانات مراقبة الجودة"""
    # Results with quality flags
    flagged_results = Result.query.filter(
        and_(
            Result.measurement_date >= start_date,
            Result.measurement_date <= end_date,
            Result.quality_flag.isnot(None)
        )
    ).all()
    
    # Group by quality flag
    flags_summary = {}
    for result in flagged_results:
        flag = result.quality_flag.value
        if flag not in flags_summary:
            flags_summary[flag] = 0
        flags_summary[flag] += 1
    
    # Results with replicates
    replicate_results = Result.query.filter(
        and_(
            Result.measurement_date >= start_date,
            Result.measurement_date <= end_date,
            Result.replicates.isnot(None)
        )
    ).count()
    
    # High CV results (>5%)
    high_cv_results = Result.query.filter(
        and_(
            Result.measurement_date >= start_date,
            Result.measurement_date <= end_date,
            Result.cv_percent > 5.0
        )
    ).count()
    
    return {
        'flags_summary': flags_summary,
        'replicate_results': replicate_results,
        'high_cv_results': high_cv_results,
        'total_flagged': len(flagged_results)
    }