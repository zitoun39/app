from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_
from datetime import datetime
import os
import json
from typing import Optional

from .models import Document, Category, DocumentVersion, SearchIndex
from .storage import file_storage
from .ocr import process_document_ocr
from app import db

# إنشاء Blueprint
archive_bp = Blueprint('archive', __name__, url_prefix='/archive')

# الملفات المسموحة
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    """التحقق من نوع الملف المسموح"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@archive_bp.route('/')
@login_required
def index():
    """الصفحة الرئيسية للأرشيف"""
    # الحصول على المعاملات
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    document_type = request.args.get('type', '')
    
    # بناء الاستعلام
    query = Document.query
    
    # تطبيق الفلاتر
    if search:
        query = query.filter(
            or_(
                Document.title.contains(search),
                Document.description.contains(search),
                Document.ocr_text.contains(search)
            )
        )
    
    if category_id:
        query = query.filter(Document.category_id == category_id)
    
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    # ترتيب النتائج
    query = query.order_by(Document.created_at.desc())
    
    # تطبيق التصفح
    documents = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # الحصول على الفئات
    categories = Category.query.all()
    
    # إحصائيات
    stats = {
        'total_documents': Document.query.count(),
        'total_categories': Category.query.count(),
        'ocr_processed': Document.query.filter(Document.ocr_processed == True).count(),
        'storage_stats': file_storage.get_storage_stats()
    }
    
    return render_template('archive/index.html',
                         documents=documents,
                         categories=categories,
                         stats=stats,
                         search=search,
                         selected_category=category_id,
                         selected_type=document_type)

@archive_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """رفع مستند جديد"""
    if request.method == 'POST':
        try:
            # التحقق من وجود الملف
            if 'file' not in request.files:
                flash('لم يتم اختيار ملف', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('لم يتم اختيار ملف', 'error')
                return redirect(request.url)
            
            if not allowed_file(file.filename):
                flash('نوع الملف غير مدعوم', 'error')
                return redirect(request.url)
            
            # الحصول على البيانات
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            document_type = request.form.get('document_type', '').strip()
            category_id = request.form.get('category_id', type=int)
            tags = request.form.get('tags', '').strip()
            access_level = request.form.get('access_level', 'public')
            is_confidential = request.form.get('is_confidential') == 'on'
            ocr_language = request.form.get('ocr_language', 'ara')
            
            # التحقق من البيانات المطلوبة
            if not title:
                flash('عنوان المستند مطلوب', 'error')
                return redirect(request.url)
            
            if not document_type:
                flash('نوع المستند مطلوب', 'error')
                return redirect(request.url)
            
            # إنشاء المستند في قاعدة البيانات
            document = Document(
                title=title,
                description=description,
                document_type=document_type,
                file_name=secure_filename(file.filename),
                category_id=category_id,
                tags=tags,
                access_level=access_level,
                is_confidential=is_confidential,
                ocr_language=ocr_language,
                uploaded_by=current_user.id
            )
            
            db.session.add(document)
            db.session.flush()  # للحصول على ID
            
            # تخزين الملف
            storage_path, file_info = file_storage.store_uploaded_file(
                file, file.filename, document.id
            )
            
            # تحديث معلومات المستند
            document.file_path = storage_path
            document.file_size = file_info.get('size', 0)
            document.mime_type = file_info.get('mime_type', '')
            
            # معالجة OCR إذا كان الملف يدعمها
            if file_info.get('extension', '').lower() in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                try:
                    full_path = file_storage.get_full_path(storage_path)
                    ocr_text, confidence = process_document_ocr(full_path, ocr_language)
                    
                    document.ocr_text = ocr_text
                    document.ocr_confidence = confidence
                    document.ocr_processed = True
                    
                    # إنشاء فهرس البحث
                    search_index = SearchIndex(
                        document_id=document.id,
                        content=f"{title} {description} {ocr_text}",
                        keywords=tags
                    )
                    db.session.add(search_index)
                    
                except Exception as e:
                    flash(f'تم رفع الملف ولكن فشل في معالجة OCR: {str(e)}', 'warning')
            
            db.session.commit()
            flash('تم رفع المستند بنجاح', 'success')
            return redirect(url_for('archive.view', id=document.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في رفع المستند: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET request
    categories = Category.query.all()
    return render_template('archive/upload.html', categories=categories)

@archive_bp.route('/document/<int:id>')
@login_required
def view(id):
    """عرض تفاصيل المستند"""
    document = Document.query.get_or_404(id)
    
    # التحقق من صلاحية الوصول
    if document.is_confidential and not current_user.has_role('admin'):
        if document.uploaded_by != current_user.id:
            abort(403)
    
    # الحصول على الإصدارات
    versions = DocumentVersion.query.filter_by(document_id=id).order_by(DocumentVersion.created_at.desc()).all()
    
    return render_template('archive/view.html', document=document, versions=versions)

@archive_bp.route('/document/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """تعديل المستند"""
    document = Document.query.get_or_404(id)
    
    # التحقق من الصلاحية
    if not current_user.has_role('admin') and document.uploaded_by != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        try:
            # الحصول على البيانات
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            document_type = request.form.get('document_type', '').strip()
            category_id = request.form.get('category_id', type=int)
            tags = request.form.get('tags', '').strip()
            access_level = request.form.get('access_level', 'public')
            is_confidential = request.form.get('is_confidential') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not title:
                flash('عنوان المستند مطلوب', 'error')
                return redirect(request.url)
            
            # تحديث البيانات
            document.title = title
            document.description = description
            document.document_type = document_type
            document.category_id = category_id
            document.tags = tags
            document.access_level = access_level
            document.is_confidential = is_confidential
            document.updated_at = datetime.utcnow()
            
            # تحديث فهرس البحث
            search_index = SearchIndex.query.filter_by(document_id=id).first()
            if search_index:
                search_index.content = f"{title} {description} {document.ocr_text or ''}"
                search_index.keywords = tags
                search_index.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('تم تحديث المستند بنجاح', 'success')
            return redirect(url_for('archive.view', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في تحديث المستند: {str(e)}', 'error')
    
    categories = Category.query.all()
    return render_template('archive/edit.html', document=document, categories=categories)

@archive_bp.route('/document/<int:id>/download')
@login_required
def download(id):
    """تحميل المستند"""
    document = Document.query.get_or_404(id)
    
    # التحقق من صلاحية الوصول
    if document.is_confidential and not current_user.has_role('admin'):
        if document.uploaded_by != current_user.id:
            abort(403)
    
    try:
        full_path = file_storage.get_full_path(document.file_path)
        if not os.path.exists(full_path):
            flash('الملف غير موجود', 'error')
            return redirect(url_for('archive.view', id=id))
        
        return send_file(full_path, as_attachment=True, download_name=document.file_name)
        
    except Exception as e:
        flash(f'خطأ في تحميل الملف: {str(e)}', 'error')
        return redirect(url_for('archive.view', id=id))

@archive_bp.route('/document/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """حذف المستند"""
    document = Document.query.get_or_404(id)
    
    # التحقق من الصلاحية
    if not current_user.has_role('admin') and document.uploaded_by != current_user.id:
        abort(403)
    
    try:
        # حذف الملف من التخزين
        file_storage.delete_file(document.file_path)
        
        # حذف الإصدارات
        for version in document.versions:
            file_storage.delete_file(version.file_path)
        
        # حذف من قاعدة البيانات
        db.session.delete(document)
        db.session.commit()
        
        flash('تم حذف المستند بنجاح', 'success')
        return redirect(url_for('archive.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ في حذف المستند: {str(e)}', 'error')
        return redirect(url_for('archive.view', id=id))

@archive_bp.route('/categories')
@login_required
def categories():
    """إدارة الفئات"""
    categories = Category.query.all()
    return render_template('archive/categories.html', categories=categories)

@archive_bp.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    """إضافة فئة جديدة"""
    if not current_user.has_role('admin'):
        abort(403)
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        parent_id = request.form.get('parent_id', type=int)
        color = request.form.get('color', '#007bff')
        icon = request.form.get('icon', '').strip()
        
        if not name:
            flash('اسم الفئة مطلوب', 'error')
            return redirect(url_for('archive.categories'))
        
        category = Category(
            name=name,
            description=description,
            parent_id=parent_id if parent_id else None,
            color=color,
            icon=icon
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('تم إضافة الفئة بنجاح', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ في إضافة الفئة: {str(e)}', 'error')
    
    return redirect(url_for('archive.categories'))

@archive_bp.route('/search')
@login_required
def search():
    """البحث المتقدم"""
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    document_type = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    results = []
    
    if query:
        # البحث في فهرس البحث
        search_results = SearchIndex.query.filter(
            or_(
                SearchIndex.content.contains(query),
                SearchIndex.keywords.contains(query)
            )
        ).all()
        
        document_ids = [result.document_id for result in search_results]
        
        if document_ids:
            documents_query = Document.query.filter(Document.id.in_(document_ids))
            
            # تطبيق الفلاتر الإضافية
            if category_id:
                documents_query = documents_query.filter(Document.category_id == category_id)
            
            if document_type:
                documents_query = documents_query.filter(Document.document_type == document_type)
            
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                    documents_query = documents_query.filter(Document.created_at >= date_from_obj)
                except ValueError:
                    pass
            
            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                    documents_query = documents_query.filter(Document.created_at <= date_to_obj)
                except ValueError:
                    pass
            
            results = documents_query.order_by(Document.created_at.desc()).all()
    
    categories = Category.query.all()
    
    return render_template('archive/search.html',
                         results=results,
                         categories=categories,
                         query=query,
                         selected_category=category_id,
                         selected_type=document_type,
                         date_from=date_from,
                         date_to=date_to)

@archive_bp.route('/api/ocr-status/<int:document_id>')
@login_required
def ocr_status(document_id):
    """حالة معالجة OCR"""
    document = Document.query.get_or_404(document_id)
    
    return jsonify({
        'processed': document.ocr_processed,
        'confidence': document.ocr_confidence,
        'text_length': len(document.ocr_text or '')
    })

@archive_bp.route('/api/reprocess-ocr/<int:document_id>', methods=['POST'])
@login_required
def reprocess_ocr(document_id):
    """إعادة معالجة OCR"""
    if not current_user.has_role('admin'):
        abort(403)
    
    document = Document.query.get_or_404(document_id)
    
    try:
        full_path = file_storage.get_full_path(document.file_path)
        language = request.json.get('language', document.ocr_language or 'ara')
        
        ocr_text, confidence = process_document_ocr(full_path, language)
        
        document.ocr_text = ocr_text
        document.ocr_confidence = confidence
        document.ocr_processed = True
        document.ocr_language = language
        document.updated_at = datetime.utcnow()
        
        # تحديث فهرس البحث
        search_index = SearchIndex.query.filter_by(document_id=document_id).first()
        if search_index:
            search_index.content = f"{document.title} {document.description} {ocr_text}"
            search_index.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'confidence': confidence,
            'text_length': len(ocr_text)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500