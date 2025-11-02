from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, case, extract
from app import db
from lims.models import Sample, Result, Parameter, Equipment

dashboard_api = Blueprint('dashboard_api', __name__)

@dashboard_api.route('/api/sample-trends')
def sample_trends():
    """توفير بيانات اتجاهات العينات خلال فترة زمنية محددة"""
    period = request.args.get('period', 30, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    # الحصول على تاريخ كل عينة
    samples = db.session.query(
        func.date(Sample.collection_date).label('date'),
        func.count(Sample.id).label('count')
    ).filter(
        Sample.collection_date >= start_date.date(),
        Sample.collection_date <= end_date.date()
    ).group_by(
        func.date(Sample.collection_date)
    ).all()
    
    # إنشاء قاموس لتخزين العدد لكل تاريخ
    date_counts = {}
    for date, count in samples:
        date_str = date.strftime('%Y-%m-%d')
        date_counts[date_str] = count
    
    # إنشاء قائمة بجميع التواريخ في النطاق
    all_dates = []
    all_counts = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        all_dates.append(date_str)
        all_counts.append(date_counts.get(date_str, 0))
        current_date += timedelta(days=1)
    
    return jsonify({
        'dates': all_dates,
        'counts': all_counts
    })

@dashboard_api.route('/api/sample-status')
def sample_status():
    """توفير بيانات توزيع حالة العينات"""
    period = request.args.get('period', 30, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    # الحصول على عدد العينات لكل حالة
    status_counts = db.session.query(
        Sample.status,
        func.count(Sample.id).label('count')
    ).filter(
        Sample.collection_date >= start_date.date(),
        Sample.collection_date <= end_date.date()
    ).group_by(
        Sample.status
    ).all()
    
    # تحويل النتائج إلى تنسيق مناسب للرسم البياني
    status_labels = {
        'registered': 'مسجلة',
        'in_progress': 'قيد التحليل',
        'completed': 'مكتملة',
        'validated': 'معتمدة',
        'reported': 'تم إصدار التقرير',
        'cancelled': 'ملغية'
    }
    
    labels = []
    counts = []
    
    for status, count in status_counts:
        labels.append(status_labels.get(status, status))
        counts.append(count)
    
    return jsonify({
        'labels': labels,
        'counts': counts
    })

@dashboard_api.route('/api/conformity-trends')
def conformity_trends():
    """توفير بيانات اتجاهات نسبة المطابقة للمعايير"""
    period = request.args.get('period', 30, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    # تجميع البيانات حسب التاريخ
    conformity_data = {}
    dates = []
    rates = []
    
    # الحصول على عدد النتائج المطابقة وغير المطابقة لكل يوم
    results_by_date = db.session.query(
        func.date(Result.measurement_date).label('date'),
        case(
            [(Result.is_conforming == True, 1)],
            else_=0
        ).label('conforming'),
        func.count().label('total')
    ).join(
        Sample, Sample.id == Result.sample_id
    ).filter(
        Sample.collection_date >= start_date.date(),
        Sample.collection_date <= end_date.date(),
        Result.measurement_date.isnot(None)
    ).group_by(
        func.date(Result.measurement_date),
        Result.is_conforming
    ).all()
    
    # تنظيم البيانات حسب التاريخ
    for date, is_conforming, count in results_by_date:
        date_str = date.strftime('%Y-%m-%d')
        if date_str not in conformity_data:
            conformity_data[date_str] = {'conforming': 0, 'total': 0}
        
        if is_conforming:
            conformity_data[date_str]['conforming'] += count
        conformity_data[date_str]['total'] += count
    
    # إنشاء قائمة بجميع التواريخ في النطاق
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        dates.append(date_str)
        
        # حساب نسبة المطابقة
        if date_str in conformity_data and conformity_data[date_str]['total'] > 0:
            conformity_rate = (conformity_data[date_str]['conforming'] / conformity_data[date_str]['total']) * 100
            rates.append(round(conformity_rate, 1))
        else:
            rates.append(0)
        
        current_date += timedelta(days=1)
    
    return jsonify({
        'dates': dates,
        'rates': rates
    })

@dashboard_api.route('/api/region-distribution')
def region_distribution():
    """توفير بيانات توزيع العينات حسب المنطقة"""
    period = request.args.get('period', 30, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    # الحصول على عدد العينات لكل منطقة (الولاية)
    region_counts = db.session.query(
        Sample.wilaya,
        func.count(Sample.id).label('count')
    ).filter(
        Sample.collection_date >= start_date.date(),
        Sample.collection_date <= end_date.date(),
        Sample.wilaya.isnot(None)
    ).group_by(
        Sample.wilaya
    ).order_by(
        func.count(Sample.id).desc()
    ).all()
    
    # تحويل النتائج إلى تنسيق مناسب للرسم البياني
    regions = []
    counts = []
    
    for region, count in region_counts:
        regions.append(region)
        counts.append(count)
    
    return jsonify({
        'regions': regions,
        'counts': counts
    })

@dashboard_api.route('/api/parameter-analysis')
def parameter_analysis():
    """توفير بيانات تحليل المعايير"""
    period = request.args.get('period', 30, type=int)
    category = request.args.get('category', 'all')
    metric = request.args.get('metric', 'avg')
    limit = request.args.get('limit', 5, type=int)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    # بناء الاستعلام الأساسي
    query = db.session.query(
        Parameter.name.label('parameter'),
        Parameter.category
    )
    
    # إضافة المقاييس المطلوبة بناءً على نوع المقياس المطلوب
    if metric == 'avg':
        query = query.add_columns(func.avg(Result.value).label('metric_value'))
        metric_label = 'متوسط القيم'
    elif metric == 'max':
        query = query.add_columns(func.max(Result.value).label('metric_value'))
        metric_label = 'القيم القصوى'
    elif metric == 'min':
        query = query.add_columns(func.min(Result.value).label('metric_value'))
        metric_label = 'القيم الدنيا'
    elif metric == 'conformity':
        query = query.add_columns(
            (func.sum(case([(Result.is_conforming == True, 1)], else_=0)) * 100 / func.count()).label('metric_value')
        )
        metric_label = 'نسبة المطابقة (%)'
    
    # الانضمام إلى الجداول المطلوبة
    query = query.join(Result, Result.parameter_id == Parameter.id)
    query = query.join(Sample, Sample.id == Result.sample_id)
    
    # تطبيق الفلاتر
    query = query.filter(Sample.collection_date >= start_date.date(), Sample.collection_date <= end_date.date())
    
    if category != 'all':
        query = query.filter(Parameter.category == category)
    
    # تجميع وترتيب النتائج
    query = query.group_by(Parameter.name, Parameter.category)
    
    if metric == 'conformity':
        query = query.order_by(func.sum(case([(Result.is_conforming == True, 1)], else_=0)) * 100 / func.count().desc())
    else:
        query = query.order_by(func.avg(Result.value).desc())
    
    # تطبيق الحد إذا كان مطلوبًا
    if limit != 'all':
        results = query.limit(limit).all()
    else:
        results = query.all()
    
    # تحويل النتائج إلى تنسيق مناسب للرسم البياني
    parameters = []
    values = []
    
    for result in results:
        parameters.append(result.parameter)
        values.append(round(result.metric_value, 2) if result.metric_value else 0)
    
    return jsonify({
        'parameters': parameters,
        'values': values,
        'metric_label': metric_label
    })