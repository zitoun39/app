# Dashboard Routes - مسارات لوحة التحكم
# Main dashboard and analytics

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, desc, asc, func
import json

from ..models import (
    db, Sample, Parameter, Result, User, Equipment, 
    SampleStatus, ResultStatus, QualityFlag, UserRole
)
from ..utils.permissions import require_role
from ..utils.helpers import format_number, get_user_permissions
from .dashboard_api import dashboard_api

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# تسجيل واجهات برمجة التطبيقات للوحة التحكم
dashboard_bp.register_blueprint(dashboard_api)

@dashboard_bp.route('/')
@login_required
def index():
    """لوحة التحكم الرئيسية"""
    # Get user permissions
    user_permissions = get_user_permissions(current_user)
    
    # Get basic statistics for the dashboard
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Sample statistics
    total_samples = Sample.query.count()
    pending_samples = Sample.query.filter_by(status=SampleStatus.PENDING).count()
    in_progress_samples = Sample.query.filter_by(status=SampleStatus.IN_PROGRESS).count()
    completed_samples = Sample.query.filter_by(status=SampleStatus.COMPLETED).count()
    validated_samples = Sample.query.filter_by(status=SampleStatus.VALIDATED).count()
    
    # Recent samples (last 7 days)
    recent_samples = Sample.query.filter(
        Sample.created_at >= datetime.combine(week_ago, datetime.min.time())
    ).count()
    
    # Overdue samples (more than 7 days in progress)
    overdue_date = today - timedelta(days=7)
    overdue_samples = Sample.query.filter(
        and_(
            Sample.status == SampleStatus.IN_PROGRESS,
            Sample.analysis_started_at <= datetime.combine(overdue_date, datetime.min.time())
        )
    ).count()
    
    # Result statistics
    total_results = Result.query.count()
    pending_results = Result.query.filter_by(status=ResultStatus.PENDING).count()
    validated_results = Result.query.filter_by(status=ResultStatus.VALIDATED).count()
    
    # Non-conforming results (last 30 days)
    non_conforming = Result.query.filter(
        and_(
            Result.measurement_date >= month_ago,
            Result.conforms_decree == False,
            Result.status == ResultStatus.VALIDATED
        )
    ).count()
    
    # Equipment needing calibration (within 30 days)
    calibration_due = Equipment.query.join(
        Equipment.calibrations
    ).filter(
        and_(
            Equipment.active == True,
            Equipment.calibrations.any(
                and_(
                    Equipment.calibrations.property.mapper.class_.active == True,
                    Equipment.calibrations.property.mapper.class_.next_calibration_date <= today + timedelta(days=30)
                )
            )
        )
    ).count()
    
    # User activity (if admin/supervisor)
    active_users = 0
    if current_user.role in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        active_users = User.query.filter(
            and_(
                User.active == True,
                User.last_login >= datetime.combine(week_ago, datetime.min.time())
            )
        ).count()
    
    dashboard_data = {
        'sample_stats': {
            'total': total_samples,
            'pending': pending_samples,
            'in_progress': in_progress_samples,
            'completed': completed_samples,
            'validated': validated_samples,
            'recent': recent_samples,
            'overdue': overdue_samples
        },
        'result_stats': {
            'total': total_results,
            'pending': pending_results,
            'validated': validated_results,
            'non_conforming': non_conforming
        },
        'equipment_stats': {
            'calibration_due': calibration_due
        },
        'user_stats': {
            'active_users': active_users
        },
        'user_permissions': user_permissions
    }
    
    return render_template('dashboard/index.html', **dashboard_data)

@dashboard_bp.route('/analytics')
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def analytics():
    """صفحة التحليلات المتقدمة"""
    return render_template('dashboard/analytics.html')

@dashboard_bp.route('/api/sample-trends')
@login_required
def sample_trends():
    """اتجاهات العينات (آخر 30 يوم)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Get daily sample counts
    daily_samples = db.session.query(
        func.date(Sample.created_at).label('date'),
        func.count(Sample.id).label('count')
    ).filter(
        Sample.created_at >= datetime.combine(start_date, datetime.min.time())
    ).group_by(
        func.date(Sample.created_at)
    ).order_by('date').all()
    
    # Fill missing dates with zero
    date_range = [start_date + timedelta(days=x) for x in range(31)]
    sample_data = {str(date_val): 0 for date_val in date_range}
    
    for date_val, count in daily_samples:
        sample_data[str(date_val)] = count
    
    return jsonify({
        'dates': list(sample_data.keys()),
        'counts': list(sample_data.values())
    })

@dashboard_bp.route('/api/result-trends')
@login_required
def result_trends():
    """اتجاهات النتائج (آخر 30 يوم)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Get daily result counts by status
    daily_results = db.session.query(
        func.date(Result.measurement_date).label('date'),
        Result.status,
        func.count(Result.id).label('count')
    ).filter(
        Result.measurement_date >= start_date
    ).group_by(
        func.date(Result.measurement_date),
        Result.status
    ).order_by('date').all()
    
    # Organize data by status
    result_data = {
        'dates': [],
        'validated': [],
        'pending': [],
        'rejected': []
    }
    
    # Fill data for each date
    date_range = [start_date + timedelta(days=x) for x in range(31)]
    for date_val in date_range:
        date_str = str(date_val)
        result_data['dates'].append(date_str)
        
        # Initialize counts
        validated_count = 0
        pending_count = 0
        rejected_count = 0
        
        # Get counts for this date
        for date_result, status, count in daily_results:
            if str(date_result) == date_str:
                if status == ResultStatus.VALIDATED:
                    validated_count = count
                elif status == ResultStatus.PENDING:
                    pending_count = count
                elif status == ResultStatus.REJECTED:
                    rejected_count = count
        
        result_data['validated'].append(validated_count)
        result_data['pending'].append(pending_count)
        result_data['rejected'].append(rejected_count)
    
    return jsonify(result_data)

@dashboard_bp.route('/api/conformity-trends')
@login_required
def conformity_trends():
    """اتجاهات المطابقة (آخر 30 يوم)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Get daily conformity rates
    daily_conformity = db.session.query(
        func.date(Result.measurement_date).label('date'),
        func.count(Result.id).label('total'),
        func.sum(func.case([(Result.conforms_decree == True, 1)], else_=0)).label('conforming')
    ).filter(
        and_(
            Result.measurement_date >= start_date,
            Result.status == ResultStatus.VALIDATED,
            Result.final_value.isnot(None)
        )
    ).group_by(
        func.date(Result.measurement_date)
    ).order_by('date').all()
    
    conformity_data = {
        'dates': [],
        'rates': []
    }
    
    for date_val, total, conforming in daily_conformity:
        conformity_data['dates'].append(str(date_val))
        rate = (conforming / total * 100) if total > 0 else 0
        conformity_data['rates'].append(round(rate, 2))
    
    return jsonify(conformity_data)

@dashboard_bp.route('/api/parameter-distribution')
@login_required
def parameter_distribution():
    """توزيع المعاملات (آخر 30 يوم)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Get parameter usage statistics
    parameter_stats = db.session.query(
        Parameter.name_ar,
        func.count(Result.id).label('count')
    ).join(Result).filter(
        Result.measurement_date >= start_date
    ).group_by(Parameter.id).order_by(
        desc('count')
    ).limit(10).all()
    
    return jsonify({
        'parameters': [name for name, count in parameter_stats],
        'counts': [count for name, count in parameter_stats]
    })

@dashboard_bp.route('/api/sample-types')
@login_required
def sample_types_distribution():
    """توزيع أنواع العينات (آخر 30 يوم)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Get sample type statistics
    sample_type_stats = db.session.query(
        Sample.sample_type.has().name_ar,
        func.count(Sample.id).label('count')
    ).filter(
        Sample.created_at >= datetime.combine(start_date, datetime.min.time())
    ).group_by(Sample.sample_type_id).all()
    
    return jsonify({
        'types': [name for name, count in sample_type_stats],
        'counts': [count for name, count in sample_type_stats]
    })

@dashboard_bp.route('/api/quality-flags')
@login_required
def quality_flags_distribution():
    """توزيع علامات الجودة (آخر 30 يوم)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Get quality flag statistics
    quality_stats = db.session.query(
        Result.quality_flag,
        func.count(Result.id).label('count')
    ).filter(
        and_(
            Result.measurement_date >= start_date,
            Result.quality_flag.isnot(None)
        )
    ).group_by(Result.quality_flag).all()
    
    flag_names = {
        QualityFlag.GOOD: 'جيد',
        QualityFlag.ACCEPTABLE: 'مقبول',
        QualityFlag.QUESTIONABLE: 'مشكوك فيه',
        QualityFlag.POOR: 'ضعيف'
    }
    
    return jsonify({
        'flags': [flag_names.get(flag, 'غير محدد') for flag, count in quality_stats],
        'counts': [count for flag, count in quality_stats]
    })

@dashboard_bp.route('/api/workload')
@login_required
@require_role(['ADMIN', 'SUPERVISOR'])
def workload_distribution():
    """توزيع أعباء العمل على المحللين"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Get analyst workload
    analyst_workload = db.session.query(
        User.full_name,
        func.count(Result.id).label('result_count'),
        func.count(Sample.id.distinct()).label('sample_count')
    ).outerjoin(
        Result, Result.analyst_id == User.id
    ).outerjoin(
        Sample, Sample.collector_id == User.id
    ).filter(
        and_(
            User.role.in_([UserRole.ANALYST, UserRole.SUPERVISOR]),
            User.active == True,
            or_(
                Result.measurement_date >= start_date,
                Sample.created_at >= datetime.combine(start_date, datetime.min.time())
            )
        )
    ).group_by(User.id).all()
    
    return jsonify({
        'analysts': [name for name, results, samples in analyst_workload],
        'results': [results for name, results, samples in analyst_workload],
        'samples': [samples for name, results, samples in analyst_workload]
    })

@dashboard_bp.route('/api/recent-activities')
@login_required
def recent_activities():
    """الأنشطة الحديثة"""
    activities = []
    
    # Recent samples (last 10)
    recent_samples = Sample.query.order_by(desc(Sample.created_at)).limit(5).all()
    for sample in recent_samples:
        activities.append({
            'type': 'sample',
            'message': f'تم إنشاء العينة {sample.sample_id}',
            'timestamp': sample.created_at,
            'user': sample.creator.full_name if sample.creator else 'غير محدد',
            'url': f'/samples/{sample.id}'
        })
    
    # Recent results (last 10)
    recent_results = Result.query.filter(
        Result.status == ResultStatus.VALIDATED
    ).order_by(desc(Result.updated_at)).limit(5).all()
    
    for result in recent_results:
        activities.append({
            'type': 'result',
            'message': f'تم اعتماد نتيجة {result.parameter.name_ar} للعينة {result.sample.sample_id}',
            'timestamp': result.updated_at,
            'user': result.validator.full_name if result.validator else 'غير محدد',
            'url': f'/samples/{result.sample_id}'
        })
    
    # Sort activities by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Format timestamps
    for activity in activities[:10]:  # Return only top 10
        activity['timestamp'] = activity['timestamp'].strftime('%Y-%m-%d %H:%M')
    
    return jsonify(activities[:10])

@dashboard_bp.route('/api/alerts')
@login_required
def system_alerts():
    """تنبيهات النظام"""
    alerts = []
    today = date.today()
    
    # Overdue samples
    overdue_date = today - timedelta(days=7)
    overdue_samples = Sample.query.filter(
        and_(
            Sample.status == SampleStatus.IN_PROGRESS,
            Sample.analysis_started_at <= datetime.combine(overdue_date, datetime.min.time())
        )
    ).count()
    
    if overdue_samples > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{overdue_samples} عينة متأخرة في التحليل',
            'url': '/samples?status=IN_PROGRESS'
        })
    
    # Equipment needing calibration
    calibration_due = Equipment.query.join(
        Equipment.calibrations
    ).filter(
        and_(
            Equipment.active == True,
            Equipment.calibrations.any(
                Equipment.calibrations.property.mapper.class_.next_calibration_date <= today + timedelta(days=30)
            )
        )
    ).count()
    
    if calibration_due > 0:
        alerts.append({
            'type': 'info',
            'message': f'{calibration_due} جهاز يحتاج معايرة خلال 30 يوم',
            'url': '/equipment'
        })
    
    # High non-conformity rate (last 7 days)
    week_ago = today - timedelta(days=7)
    total_recent = Result.query.filter(
        and_(
            Result.measurement_date >= week_ago,
            Result.status == ResultStatus.VALIDATED,
            Result.final_value.isnot(None)
        )
    ).count()
    
    non_conforming_recent = Result.query.filter(
        and_(
            Result.measurement_date >= week_ago,
            Result.status == ResultStatus.VALIDATED,
            Result.conforms_decree == False
        )
    ).count()
    
    if total_recent > 0:
        non_conformity_rate = (non_conforming_recent / total_recent) * 100
        if non_conformity_rate > 20:  # Alert if > 20% non-conformity
            alerts.append({
                'type': 'danger',
                'message': f'معدل عدم المطابقة مرتفع: {non_conformity_rate:.1f}%',
                'url': '/reports/compliance'
            })
    
    return jsonify(alerts)

@dashboard_bp.route('/api/performance-metrics')
@login_required
@require_role(['ADMIN', 'SUPERVISOR'])
def performance_metrics():
    """مؤشرات الأداء"""
    today = date.today()
    month_ago = today - timedelta(days=30)
    
    # Average turnaround time
    completed_samples = Sample.query.filter(
        and_(
            Sample.status.in_([SampleStatus.COMPLETED, SampleStatus.VALIDATED]),
            Sample.analysis_completed_at.isnot(None),
            Sample.analysis_started_at.isnot(None),
            Sample.created_at >= datetime.combine(month_ago, datetime.min.time())
        )
    ).all()
    
    if completed_samples:
        turnaround_times = []
        for sample in completed_samples:
            duration = sample.analysis_completed_at - sample.analysis_started_at
            turnaround_times.append(duration.total_seconds() / 3600)  # Convert to hours
        
        avg_turnaround = sum(turnaround_times) / len(turnaround_times)
    else:
        avg_turnaround = 0
    
    # Sample throughput (samples per day)
    total_samples_month = Sample.query.filter(
        Sample.created_at >= datetime.combine(month_ago, datetime.min.time())
    ).count()
    
    throughput = total_samples_month / 30  # Samples per day
    
    # Validation rate
    total_results_month = Result.query.filter(
        Result.measurement_date >= month_ago
    ).count()
    
    validated_results_month = Result.query.filter(
        and_(
            Result.measurement_date >= month_ago,
            Result.status == ResultStatus.VALIDATED
        )
    ).count()
    
    validation_rate = (validated_results_month / total_results_month * 100) if total_results_month > 0 else 0
    
    return jsonify({
        'avg_turnaround_hours': round(avg_turnaround, 2),
        'daily_throughput': round(throughput, 2),
        'validation_rate': round(validation_rate, 2),
        'total_samples_month': total_samples_month,
        'validated_results_month': validated_results_month
    })