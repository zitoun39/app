# Samples Routes - مسارات العينات
# Sample management, registration, and tracking

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, desc, asc
import json

from ..models import db, Sample, SampleType, SampleStatus, Parameter, Result, User
from ..utils.helpers import generate_sample_code, get_client_ip
from ..utils.validators import validate_sample_data
from ..utils.permissions import require_role, can_edit_sample, can_validate_sample

samples_bp = Blueprint('samples', __name__, url_prefix='/samples')

@samples_bp.route('/')
@login_required
def index():
    """قائمة العينات"""
    # Get filter parameters
    status = request.args.get('status', '')
    sample_type = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query
    query = Sample.query
    
    # Apply filters
    if status:
        query = query.filter(Sample.status == SampleStatus(status))
    
    if sample_type:
        query = query.filter(Sample.sample_type_id == sample_type)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Sample.collection_date >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Sample.collection_date <= date_to_obj)
        except ValueError:
            pass
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            or_(
                Sample.sample_id.ilike(search_term),
                Sample.location_name.ilike(search_term),
                Sample.commune.ilike(search_term),
                Sample.client_name.ilike(search_term)
            )
        )
    
    # Order by creation date (newest first)
    query = query.order_by(desc(Sample.created_at))
    
    # Paginate
    samples = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get sample types for filter
    sample_types = SampleType.query.filter_by(active=True).all()
    
    return render_template('samples/index.html', 
                         samples=samples, 
                         sample_types=sample_types,
                         SampleStatus=SampleStatus,
                         filters={
                             'status': status,
                             'type': sample_type,
                             'date_from': date_from,
                             'date_to': date_to,
                             'search': search
                         })

@samples_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'ANALYST'])
def create():
    """إنشاء عينة جديدة"""
    if request.method == 'POST':
        try:
            # Get form data
            sample_data = {
                'sample_type_id': request.form.get('sample_type_id', type=int),
                'collection_date': datetime.strptime(request.form.get('collection_date'), '%Y-%m-%d').date(),
                'location_name': request.form.get('location_name', '').strip(),
                'commune': request.form.get('commune', '').strip(),
                'wilaya': request.form.get('wilaya', 'سطيف').strip(),
                'client_name': request.form.get('client_name', '').strip(),
                'client_phone': request.form.get('client_phone', '').strip(),
                'client_address': request.form.get('client_address', '').strip(),
                'analysis_type': request.form.get('analysis_type', 'complete'),
                'temperature': request.form.get('temperature', type=float),
                'ph_field': request.form.get('ph_field', type=float),
                'conductivity_field': request.form.get('conductivity_field', type=float),
                'weather_conditions': request.form.get('weather_conditions', '').strip(),
                'transport_conditions': request.form.get('transport_conditions', '').strip(),
                'sampling_method': request.form.get('sampling_method', '').strip(),
                'preservation_method': request.form.get('preservation_method', '').strip(),
                'comments': request.form.get('comments', '').strip(),
                'urgent': bool(request.form.get('urgent')),
                'collector_id': current_user.id,
                'created_by': current_user.id
            }
            
            # Validate data
            validation_result = validate_sample_data(sample_data)
            if not validation_result['valid']:
                flash(f'خطأ في البيانات: {validation_result["message"]}', 'error')
                return render_template('samples/create.html', 
                                     sample_types=SampleType.query.filter_by(active=True).all(),
                                     form_data=sample_data)
            
            # Generate sample ID
            sample_type = SampleType.query.get(sample_data['sample_type_id'])
            sample_id = generate_sample_code(sample_type.code, sample_data['collection_date'])
            sample_data['sample_id'] = sample_id
            
            # Create sample
            sample = Sample(**sample_data)
            db.session.add(sample)
            db.session.flush()  # Get the sample ID
            
            # Create default parameter results based on analysis type
            create_default_results(sample)
            
            db.session.commit()
            
            flash(f'تم إنشاء العينة {sample_id} بنجاح', 'success')
            return redirect(url_for('samples.view', id=sample.id))
            
        except ValueError as e:
            flash(f'خطأ في التاريخ: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'error')
    
    # GET request - show form
    sample_types = SampleType.query.filter_by(active=True).all()
    return render_template('samples/create.html', sample_types=sample_types)

@samples_bp.route('/<int:id>')
@login_required
def view(id):
    """عرض تفاصيل العينة"""
    sample = Sample.query.get_or_404(id)
    
    # Get results grouped by category
    results = Result.query.filter_by(sample_id=id).join(Parameter).order_by(Parameter.category, Parameter.display_order).all()
    
    # Group results by category
    results_by_category = {}
    for result in results:
        category = result.parameter.category
        if category not in results_by_category:
            results_by_category[category] = []
        results_by_category[category].append(result)
    
    # Check permissions
    can_edit = can_edit_sample(sample, current_user)
    can_validate = can_validate_sample(sample, current_user)
    
    return render_template('samples/view.html', 
                         sample=sample, 
                         results_by_category=results_by_category,
                         can_edit=can_edit,
                         can_validate=can_validate)

@samples_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """تعديل العينة"""
    sample = Sample.query.get_or_404(id)
    
    # Check permissions
    if not can_edit_sample(sample, current_user):
        flash('غير مصرح لك بتعديل هذه العينة', 'error')
        return redirect(url_for('samples.view', id=id))
    
    if request.method == 'POST':
        try:
            # Update sample data
            sample.location_name = request.form.get('location_name', '').strip()
            sample.commune = request.form.get('commune', '').strip()
            sample.wilaya = request.form.get('wilaya', '').strip()
            sample.client_name = request.form.get('client_name', '').strip()
            sample.client_phone = request.form.get('client_phone', '').strip()
            sample.client_address = request.form.get('client_address', '').strip()
            sample.temperature = request.form.get('temperature', type=float)
            sample.ph_field = request.form.get('ph_field', type=float)
            sample.conductivity_field = request.form.get('conductivity_field', type=float)
            sample.weather_conditions = request.form.get('weather_conditions', '').strip()
            sample.transport_conditions = request.form.get('transport_conditions', '').strip()
            sample.sampling_method = request.form.get('sampling_method', '').strip()
            sample.preservation_method = request.form.get('preservation_method', '').strip()
            sample.comments = request.form.get('comments', '').strip()
            sample.urgent = bool(request.form.get('urgent'))
            sample.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('تم تحديث العينة بنجاح', 'success')
            return redirect(url_for('samples.view', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'error')
    
    return render_template('samples/edit.html', sample=sample)

@samples_bp.route('/<int:id>/start-analysis', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'ANALYST'])
def start_analysis(id):
    """بدء تحليل العينة"""
    sample = Sample.query.get_or_404(id)
    
    if sample.status != SampleStatus.PENDING:
        return jsonify({'success': False, 'message': 'لا يمكن بدء التحليل لهذه العينة'}), 400
    
    try:
        sample.start_analysis(current_user.id)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم بدء التحليل بنجاح',
            'status': sample.status.value
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@samples_bp.route('/<int:id>/complete-analysis', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'ANALYST'])
def complete_analysis(id):
    """إكمال تحليل العينة"""
    sample = Sample.query.get_or_404(id)
    
    if sample.status != SampleStatus.IN_PROGRESS:
        return jsonify({'success': False, 'message': 'العينة ليست قيد التحليل'}), 400
    
    try:
        sample.complete_analysis()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إكمال التحليل بنجاح',
            'status': sample.status.value
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@samples_bp.route('/<int:id>/validate', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'VALIDATOR'])
def validate_sample(id):
    """اعتماد العينة"""
    sample = Sample.query.get_or_404(id)
    
    if not can_validate_sample(sample, current_user):
        return jsonify({'success': False, 'message': 'غير مصرح لك باعتماد هذه العينة'}), 403
    
    if sample.status != SampleStatus.COMPLETED:
        return jsonify({'success': False, 'message': 'العينة غير مكتملة التحليل'}), 400
    
    try:
        comments = request.json.get('comments', '') if request.is_json else ''
        sample.validate_sample(current_user.id, comments)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم اعتماد العينة بنجاح',
            'status': sample.status.value
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@samples_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR'])
def cancel_sample(id):
    """إلغاء العينة"""
    sample = Sample.query.get_or_404(id)
    
    if sample.status == SampleStatus.VALIDATED:
        return jsonify({'success': False, 'message': 'لا يمكن إلغاء عينة معتمدة'}), 400
    
    try:
        reason = request.json.get('reason', '') if request.is_json else 'تم الإلغاء'
        sample.cancel_sample(reason)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إلغاء العينة بنجاح',
            'status': sample.status.value
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@samples_bp.route('/<int:id>/duplicate', methods=['POST'])
@login_required
@require_role(['ADMIN', 'SUPERVISOR', 'ANALYST'])
def duplicate_sample(id):
    """تكرار العينة"""
    original_sample = Sample.query.get_or_404(id)
    
    try:
        new_sample = original_sample.create_duplicate(current_user.id)
        db.session.add(new_sample)
        db.session.flush()
        
        # Create default results for the new sample
        create_default_results(new_sample)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم إنشاء العينة المكررة {new_sample.sample_id}',
            'new_sample_id': new_sample.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@samples_bp.route('/<int:id>/print-label')
@login_required
def print_label(id):
    """طباعة ملصق العينة"""
    sample = Sample.query.get_or_404(id)
    return render_template('samples/label.html', sample=sample)

@samples_bp.route('/dashboard-data')
@login_required
def dashboard_data():
    """بيانات لوحة التحكم للعينات"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Sample counts by status
    status_counts = {}
    for status in SampleStatus:
        count = Sample.query.filter_by(status=status).count()
        status_counts[status.value] = count
    
    # Recent samples
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
    
    # Samples by type (last 30 days)
    samples_by_type = db.session.query(
        SampleType.name_ar,
        db.func.count(Sample.id).label('count')
    ).join(Sample).filter(
        Sample.created_at >= datetime.combine(month_ago, datetime.min.time())
    ).group_by(SampleType.id).all()
    
    return jsonify({
        'status_counts': status_counts,
        'recent_samples': recent_samples,
        'overdue_samples': overdue_samples,
        'samples_by_type': [{'name': name, 'count': count} for name, count in samples_by_type]
    })

@samples_bp.route('/search')
@login_required
def search():
    """البحث في العينات (AJAX)"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify({'samples': []})
    
    search_term = f'%{query}%'
    samples = Sample.query.filter(
        or_(
            Sample.sample_id.ilike(search_term),
            Sample.location_name.ilike(search_term),
            Sample.commune.ilike(search_term),
            Sample.client_name.ilike(search_term)
        )
    ).limit(10).all()
    
    results = []
    for sample in samples:
        results.append({
            'id': sample.id,
            'sample_id': sample.sample_id,
            'location_name': sample.location_name,
            'collection_date': sample.collection_date.isoformat(),
            'status': sample.status.value,
            'client_name': sample.client_name
        })
    
    return jsonify({'samples': results})

# Helper functions
def create_default_results(sample):
    """إنشاء نتائج افتراضية للعينة"""
    # Get parameters based on analysis type
    query = Parameter.query.filter_by(active=True)
    
    if sample.analysis_type == 'partial':
        query = query.filter_by(in_partial=True)
    elif sample.analysis_type == 'bacteriological':
        query = query.filter_by(in_bacteriological=True)
    elif sample.analysis_type == 'complete':
        query = query.filter_by(in_complete=True)
    
    parameters = query.all()
    
    # Create result records
    for parameter in parameters:
        result = Result(
            sample_id=sample.id,
            parameter_id=parameter.id,
            entered_by=sample.created_by
        )
        db.session.add(result)

# Context processors
@samples_bp.app_context_processor
def inject_sample_enums():
    """حقن تعدادات العينات في القوالب"""
    return {
        'SampleStatus': SampleStatus
    }