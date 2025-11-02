# Results Routes - مسارات النتائج
# Laboratory test results management and data entry

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, desc, asc
import json
from decimal import Decimal, InvalidOperation

from ..models import db, Sample, Parameter, Result, ResultStatus, QualityFlag, Equipment
from ..utils.helpers import format_number, calculate_uncertainty
from ..utils.validators import validate_result_value
from ..utils.permissions import require_role, can_edit_result, can_validate_result
from ..utils.calculations import calculate_parameter_value, check_conformity

results_bp = Blueprint('results', __name__, url_prefix='/results')

@results_bp.route('/')
@login_required
def index():
    """قائمة النتائج"""
    # Get filter parameters
    status = request.args.get('status', '')
    parameter_id = request.args.get('parameter', '', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Build query
    query = Result.query.join(Sample).join(Parameter)
    
    # Apply filters
    if status:
        query = query.filter(Result.status == ResultStatus(status))
    
    if parameter_id:
        query = query.filter(Result.parameter_id == parameter_id)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Result.measurement_date >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Result.measurement_date <= date_to_obj)
        except ValueError:
            pass
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            or_(
                Sample.sample_id.ilike(search_term),
                Parameter.name_ar.ilike(search_term),
                Parameter.name_en.ilike(search_term)
            )
        )
    
    # Order by measurement date (newest first)
    query = query.order_by(desc(Result.measurement_date), desc(Result.created_at))
    
    # Paginate
    results = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get parameters for filter
    parameters = Parameter.query.filter_by(active=True).order_by(Parameter.name_ar).all()
    
    return render_template('results/index.html', 
                         results=results, 
                         parameters=parameters,
                         ResultStatus=ResultStatus,
                         QualityFlag=QualityFlag,
                         filters={
                             'status': status,
                             'parameter': parameter_id,
                             'date_from': date_from,
                             'date_to': date_to,
                             'search': search
                         })

@results_bp.route('/sample/<int:sample_id>')
@login_required
def sample_results(sample_id):
    """نتائج عينة محددة"""
    sample = Sample.query.get_or_404(sample_id)
    
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
    
    # Check permissions
    can_edit = can_edit_result(sample, current_user)
    can_validate = can_validate_result(sample, current_user)
    
    return render_template('results/sample_results.html', 
                         sample=sample,
                         results_by_category=results_by_category,
                         can_edit=can_edit,
                         can_validate=can_validate)

@results_bp.route('/edit/<int:result_id>', methods=['GET', 'POST'])
@login_required
def edit(result_id):
    """تعديل نتيجة"""
    result = Result.query.get_or_404(result_id)
    
    # Check permissions
    if not can_edit_result(result.sample, current_user):
        flash('غير مصرح لك بتعديل هذه النتيجة', 'error')
        return redirect(url_for('results.sample_results', sample_id=result.sample_id))
    
    if request.method == 'POST':
        try:
            # Get form data
            raw_value = request.form.get('raw_value', '').strip()
            text_value = request.form.get('text_value', '').strip()
            dilution_factor = request.form.get('dilution_factor', 1.0, type=float)
            equipment_id = request.form.get('equipment_id', type=int) or None
            method = request.form.get('method', '').strip()
            comments = request.form.get('comments', '').strip()
            
            # Validate and convert raw value
            if raw_value:
                validation_result = validate_result_value(raw_value, result.parameter)
                if not validation_result['valid']:
                    flash(f'قيمة غير صحيحة: {validation_result["message"]}', 'error')
                    return render_template('results/edit.html', 
                                         result=result,
                                         equipment_list=Equipment.query.filter_by(active=True).all())
                
                result.raw_value = Decimal(str(validation_result['value']))
                result.text_value = None
            elif text_value:
                result.text_value = text_value
                result.raw_value = None
            else:
                flash('يجب إدخال قيمة رقمية أو نصية', 'error')
                return render_template('results/edit.html', 
                                     result=result,
                                     equipment_list=Equipment.query.filter_by(active=True).all())
            
            # Update other fields
            result.dilution_factor = dilution_factor
            result.equipment_id = equipment_id
            result.method = method
            result.comments = comments
            result.measurement_date = date.today()
            result.measurement_time = datetime.now().time()
            result.analyst_id = current_user.id
            result.updated_at = datetime.utcnow()
            
            # Calculate final value and check conformity
            if result.raw_value is not None:
                result.final_value = calculate_parameter_value(result)
                result.conforms_decree = check_conformity(result, 'decree')
                result.conforms_who = check_conformity(result, 'who')
            
            # Update status
            if result.status == ResultStatus.PENDING:
                result.status = ResultStatus.ENTERED
            
            db.session.commit()
            
            flash('تم تحديث النتيجة بنجاح', 'success')
            return redirect(url_for('results.sample_results', sample_id=result.sample_id))
            
        except (ValueError, InvalidOperation) as e:
            flash(f'خطأ في القيمة المدخلة: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'error')
    
    # GET request - show form
    equipment_list = Equipment.query.filter_by(active=True).all()
    return render_template('results/edit.html', result=result, equipment_list=equipment_list)

@results_bp.route('/batch-edit/<int:sample_id>', methods=['GET', 'POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'ANALYST'])
def batch_edit(sample_id):
    """تعديل مجموعي للنتائج"""
    sample = Sample.query.get_or_404(sample_id)
    
    # Check permissions
    if not can_edit_result(sample, current_user):
        flash('غير مصرح لك بتعديل نتائج هذه العينة', 'error')
        return redirect(url_for('results.sample_results', sample_id=sample_id))
    
    if request.method == 'POST':
        try:
            # Get form data
            results_data = request.form.to_dict()
            updated_count = 0
            
            # Process each result
            for key, value in results_data.items():
                if key.startswith('result_') and value.strip():
                    result_id = int(key.split('_')[1])
                    result = Result.query.get(result_id)
                    
                    if result and result.sample_id == sample_id:
                        # Validate and update value
                        validation_result = validate_result_value(value.strip(), result.parameter)
                        if validation_result['valid']:
                            result.raw_value = Decimal(str(validation_result['value']))
                            result.text_value = None
                            result.final_value = calculate_parameter_value(result)
                            result.conforms_decree = check_conformity(result, 'decree')
                            result.conforms_who = check_conformity(result, 'who')
                            result.measurement_date = date.today()
                            result.measurement_time = datetime.now().time()
                            result.analyst_id = current_user.id
                            result.updated_at = datetime.utcnow()
                            
                            if result.status == ResultStatus.PENDING:
                                result.status = ResultStatus.ENTERED
                            
                            updated_count += 1
            
            db.session.commit()
            
            flash(f'تم تحديث {updated_count} نتيجة بنجاح', 'success')
            return redirect(url_for('results.sample_results', sample_id=sample_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'error')
    
    # GET request - show form
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
    
    return render_template('results/batch_edit.html', 
                         sample=sample,
                         results_by_category=results_by_category)

@results_bp.route('/validate/<int:result_id>', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def validate_result(result_id):
    """اعتماد نتيجة"""
    result = Result.query.get_or_404(result_id)
    
    # Check permissions
    if not can_validate_result(result.sample, current_user):
        return jsonify({'success': False, 'message': 'غير مصرح لك باعتماد هذه النتيجة'}), 403
    
    if result.status not in [ResultStatus.ENTERED, ResultStatus.REVIEWED]:
        return jsonify({'success': False, 'message': 'النتيجة غير جاهزة للاعتماد'}), 400
    
    try:
        comments = request.json.get('comments', '') if request.is_json else ''
        result.validate_result(current_user.id, comments)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم اعتماد النتيجة بنجاح',
            'status': result.status.value
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@results_bp.route('/reject/<int:result_id>', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def reject_result(result_id):
    """رفض نتيجة"""
    result = Result.query.get_or_404(result_id)
    
    # Check permissions
    if not can_validate_result(result.sample, current_user):
        return jsonify({'success': False, 'message': 'غير مصرح لك برفض هذه النتيجة'}), 403
    
    try:
        reason = request.json.get('reason', 'تم الرفض') if request.is_json else 'تم الرفض'
        result.reject_result(current_user.id, reason)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم رفض النتيجة بنجاح',
            'status': result.status.value
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@results_bp.route('/flag/<int:result_id>', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'ANALYST'])
def flag_result(result_id):
    """وضع علامة جودة على النتيجة"""
    result = Result.query.get_or_404(result_id)
    
    try:
        flag = request.json.get('flag') if request.is_json else None
        comments = request.json.get('comments', '') if request.is_json else ''
        
        if flag and flag in [f.value for f in QualityFlag]:
            result.flag_quality(QualityFlag(flag), current_user.id, comments)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'تم وضع العلامة بنجاح',
                'flag': result.quality_flag.value if result.quality_flag else None
            })
        else:
            return jsonify({'success': False, 'message': 'علامة جودة غير صحيحة'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@results_bp.route('/add-replicate/<int:result_id>', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'ANALYST'])
def add_replicate(result_id):
    """إضافة تكرار للنتيجة"""
    result = Result.query.get_or_404(result_id)
    
    # Check permissions
    if not can_edit_result(result.sample, current_user):
        return jsonify({'success': False, 'message': 'غير مصرح لك بتعديل هذه النتيجة'}), 403
    
    try:
        value = request.json.get('value') if request.is_json else None
        
        if value is not None:
            # Validate value
            validation_result = validate_result_value(str(value), result.parameter)
            if not validation_result['valid']:
                return jsonify({'success': False, 'message': validation_result['message']}), 400
            
            result.add_replicate(Decimal(str(validation_result['value'])))
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'تم إضافة التكرار بنجاح',
                'replicates': result.replicates,
                'std_deviation': float(result.std_deviation) if result.std_deviation else None,
                'cv_percent': float(result.cv_percent) if result.cv_percent else None
            })
        else:
            return jsonify({'success': False, 'message': 'قيمة التكرار مطلوبة'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@results_bp.route('/statistics/<int:parameter_id>')
@login_required
def parameter_statistics(parameter_id):
    """إحصائيات المعامل"""
    parameter = Parameter.query.get_or_404(parameter_id)
    
    # Get date range
    days = request.args.get('days', 30, type=int)
    start_date = date.today() - timedelta(days=days)
    
    # Get results for this parameter
    results = Result.query.filter(
        and_(
            Result.parameter_id == parameter_id,
            Result.measurement_date >= start_date,
            Result.final_value.isnot(None),
            Result.status == ResultStatus.VALIDATED
        )
    ).order_by(Result.measurement_date).all()
    
    if not results:
        return jsonify({
            'parameter': parameter.name_ar,
            'count': 0,
            'statistics': None
        })
    
    # Calculate statistics
    values = [float(r.final_value) for r in results]
    
    statistics = {
        'count': len(values),
        'min': min(values),
        'max': max(values),
        'mean': sum(values) / len(values),
        'median': sorted(values)[len(values) // 2],
        'conformity_rate': sum(1 for r in results if r.conforms_decree) / len(results) * 100
    }
    
    # Calculate standard deviation
    if len(values) > 1:
        mean = statistics['mean']
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        statistics['std_deviation'] = variance ** 0.5
    else:
        statistics['std_deviation'] = 0
    
    # Prepare chart data
    chart_data = []
    for result in results:
        chart_data.append({
            'date': result.measurement_date.isoformat(),
            'value': float(result.final_value),
            'sample_id': result.sample.sample_id,
            'conforms': result.conforms_decree
        })
    
    return jsonify({
        'parameter': parameter.name_ar,
        'unit': parameter.unit,
        'statistics': statistics,
        'chart_data': chart_data,
        'limits': {
            'decree_max': float(parameter.decree_max) if parameter.decree_max else None,
            'who_max': float(parameter.who_max) if parameter.who_max else None
        }
    })

@results_bp.route('/export/<int:sample_id>')
@login_required
def export_results(sample_id):
    """تصدير نتائج العينة"""
    sample = Sample.query.get_or_404(sample_id)
    
    # Get results
    results = Result.query.filter_by(sample_id=sample_id).join(Parameter).order_by(
        Parameter.category, Parameter.display_order
    ).all()
    
    # Prepare export data
    export_data = {
        'sample': {
            'id': sample.sample_id,
            'location': sample.location_name,
            'collection_date': sample.collection_date.isoformat(),
            'client': sample.client_name
        },
        'results': []
    }
    
    for result in results:
        export_data['results'].append({
            'parameter': result.parameter.name_ar,
            'value': result.get_display_value(),
            'unit': result.parameter.unit,
            'method': result.method,
            'conforms_decree': result.conforms_decree,
            'status': result.status.value
        })
    
    return jsonify(export_data)

@results_bp.route('/dashboard-data')
@login_required
def dashboard_data():
    """بيانات لوحة التحكم للنتائج"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Result counts by status
    status_counts = {}
    for status in ResultStatus:
        count = Result.query.filter_by(status=status).count()
        status_counts[status.value] = count
    
    # Recent results
    recent_results = Result.query.filter(
        Result.measurement_date >= week_ago
    ).count()
    
    # Non-conforming results (last 30 days)
    non_conforming = Result.query.filter(
        and_(
            Result.measurement_date >= month_ago,
            Result.conforms_decree == False,
            Result.status == ResultStatus.VALIDATED
        )
    ).count()
    
    # Results by quality flag
    quality_flags = db.session.query(
        Result.quality_flag,
        db.func.count(Result.id).label('count')
    ).filter(
        and_(
            Result.quality_flag.isnot(None),
            Result.measurement_date >= month_ago
        )
    ).group_by(Result.quality_flag).all()
    
    return jsonify({
        'status_counts': status_counts,
        'recent_results': recent_results,
        'non_conforming': non_conforming,
        'quality_flags': [{'flag': flag.value if flag else 'none', 'count': count} 
                         for flag, count in quality_flags]
    })

# Context processors
@results_bp.app_context_processor
def inject_result_enums():
    """حقن تعدادات النتائج في القوالب"""
    return {
        'ResultStatus': ResultStatus,
        'QualityFlag': QualityFlag
    }