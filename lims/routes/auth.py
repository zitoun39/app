# Authentication Routes - مسارات المصادقة
# User login, logout, and session management

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import re

from ..models import User, UserRole

# Import db to avoid circular imports
try:
    from app import db
except ImportError:
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()

# Placeholder functions for utils (will implement basic versions)
def validate_password_strength(password):
    """Basic password validation"""
    return {
        'valid': len(password) >= 8,
        'message': 'كلمة مرور ضعيفة - يجب أن تكون 8 أحرف على الأقل'
    }

def log_security_event(event_type, user_id, ip_address, details=None):
    """Basic security event logging"""
    print(f"Security Event: {event_type}, User: {user_id}, IP: {ip_address}")

def get_client_ip():
    """Get client IP address"""
    from flask import request
    return request.remote_addr or 'unknown'

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Login rate limiting
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=30)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))
        
        # Validate input
        if not username or not password:
            flash('يرجى إدخال اسم المستخدم وكلمة المرور', 'error')
            return render_template('auth/login.html')
        
        # Check rate limiting
        client_ip = get_client_ip()
        if is_ip_locked(client_ip):
            flash('تم حظر عنوان IP مؤقتاً بسبب محاولات دخول متكررة', 'error')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user and user.is_active and check_password_hash(user.password_hash, password):
            # Check if account is locked
            if user.is_account_locked():
                flash('الحساب مقفل. يرجى الاتصال بالمدير', 'error')
                log_security_event('login_attempt_locked_account', user.id, client_ip)
                return render_template('auth/login.html')
            
            # Successful login
            login_user(user, remember=remember_me)
            
            # Update user login info
            user.last_login = datetime.utcnow()
            user.failed_login_attempts = 0
            db.session.commit()
            
            # Clear rate limiting
            if client_ip in login_attempts:
                del login_attempts[client_ip]
            
            # Log successful login
            log_security_event('login_success', user.id, client_ip)
            
            # Redirect to intended page or dashboard
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            
            flash(f'مرحباً {user.full_name}', 'success')
            return redirect(url_for('dashboard.index'))
        
        else:
            # Failed login
            record_failed_login(client_ip, username)
            
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                    user.locked_until = datetime.utcnow() + LOCKOUT_DURATION
                    flash('تم قفل الحساب بسبب محاولات دخول متكررة', 'error')
                    log_security_event('account_locked', user.id, client_ip)
                else:
                    remaining = MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
                    flash(f'اسم المستخدم أو كلمة المرور غير صحيحة. المحاولات المتبقية: {remaining}', 'error')
                
                db.session.commit()
                log_security_event('login_failed', user.id, client_ip)
            else:
                flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
                log_security_event('login_failed_unknown_user', None, client_ip, {'username': username})
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """تسجيل الخروج"""
    user_id = current_user.id
    client_ip = get_client_ip()
    
    logout_user()
    session.clear()
    
    log_security_event('logout', user_id, client_ip)
    flash('تم تسجيل الخروج بنجاح', 'info')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """تغيير كلمة المرور"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not check_password_hash(current_user.password_hash, current_password):
            flash('كلمة المرور الحالية غير صحيحة', 'error')
            return render_template('auth/change_password.html')
        
        # Validate new password
        if new_password != confirm_password:
            flash('كلمة المرور الجديدة وتأكيدها غير متطابقين', 'error')
            return render_template('auth/change_password.html')
        
        # Check password strength
        strength_result = validate_password_strength(new_password)
        if not strength_result['valid']:
            flash(f'كلمة المرور ضعيفة: {strength_result["message"]}', 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        current_user.password_changed_at = datetime.utcnow()
        current_user.force_password_change = False
        db.session.commit()
        
        log_security_event('password_changed', current_user.id, get_client_ip())
        flash('تم تغيير كلمة المرور بنجاح', 'success')
        
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/change_password.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """الملف الشخصي"""
    if request.method == 'POST':
        # Update profile information
        current_user.full_name = request.form.get('full_name', '').strip()
        current_user.email = request.form.get('email', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        
        # Validate email format
        if current_user.email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', current_user.email):
            flash('صيغة البريد الإلكتروني غير صحيحة', 'error')
            return render_template('auth/profile.html')
        
        # Handle signature upload
        if 'signature' in request.files:
            signature_file = request.files['signature']
            if signature_file and signature_file.filename:
                # Process signature file (convert to base64)
                import base64
                signature_data = base64.b64encode(signature_file.read()).decode('utf-8')
                current_user.signature = signature_data
        
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح', 'success')
        
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

@auth_bp.route('/users')
@login_required
def users_list():
    """قائمة المستخدمين (للمدراء فقط)"""
    if current_user.role != UserRole.ADMIN:
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'error')
        return redirect(url_for('dashboard.index'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/users_list.html', users=users)

@auth_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """إنشاء مستخدم جديد (للمدراء فقط)"""
    if current_user.role != UserRole.ADMIN:
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'error')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', '')
        password = request.form.get('password', '')
        
        # Validate input
        if not all([username, full_name, role, password]):
            flash('يرجى ملء جميع الحقول المطلوبة', 'error')
            return render_template('auth/create_user.html')
        
        # Check if username exists
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود مسبقاً', 'error')
            return render_template('auth/create_user.html')
        
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            flash('الدور المحدد غير صحيح', 'error')
            return render_template('auth/create_user.html')
        
        # Validate password strength
        strength_result = validate_password_strength(password)
        if not strength_result['valid']:
            flash(f'كلمة المرور ضعيفة: {strength_result["message"]}', 'error')
            return render_template('auth/create_user.html')
        
        # Create user
        user = User(
            username=username,
            email=email,
            password=password,
            first_name=full_name.split()[0] if full_name.split() else full_name,
            last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
            role=user_role
        )
        user.phone = phone
        user.is_active = True
        user.is_verified = False
        
        db.session.add(user)
        db.session.commit()
        
        log_security_event('user_created', current_user.id, get_client_ip(), {'new_user_id': user.id})
        flash(f'تم إنشاء المستخدم {username} بنجاح', 'success')
        
        return redirect(url_for('auth.users_list'))
    
    return render_template('auth/create_user.html', roles=UserRole)

@auth_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """تفعيل/إلغاء تفعيل المستخدم"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Cannot deactivate self
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'لا يمكن إلغاء تفعيل حسابك الخاص'}), 400
    
    user.active = not user.active
    db.session.commit()
    
    action = 'activated' if user.active else 'deactivated'
    log_security_event(f'user_{action}', current_user.id, get_client_ip(), {'target_user_id': user.id})
    
    status_text = 'مفعل' if user.active else 'معطل'
    return jsonify({
        'success': True, 
        'message': f'تم {status_text} المستخدم بنجاح',
        'active': user.active
    })

@auth_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """إعادة تعيين كلمة مرور المستخدم"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Generate temporary password
    import secrets
    import string
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    
    user.password_hash = generate_password_hash(temp_password)
    user.is_verified = False
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
    
    log_security_event('password_reset', current_user.id, get_client_ip(), {'target_user_id': user.id})
    
    return jsonify({
        'success': True,
        'message': 'تم إعادة تعيين كلمة المرور',
        'temp_password': temp_password
    })

# Helper functions
def is_ip_locked(ip_address):
    """فحص ما إذا كان عنوان IP محظور"""
    if ip_address not in login_attempts:
        return False
    
    attempts = login_attempts[ip_address]
    if attempts['count'] >= MAX_LOGIN_ATTEMPTS:
        if datetime.now() - attempts['last_attempt'] < LOCKOUT_DURATION:
            return True
        else:
            # Reset attempts after lockout period
            del login_attempts[ip_address]
    
    return False

def record_failed_login(ip_address, username):
    """تسجيل محاولة دخول فاشلة"""
    if ip_address not in login_attempts:
        login_attempts[ip_address] = {'count': 0, 'last_attempt': None}
    
    login_attempts[ip_address]['count'] += 1
    login_attempts[ip_address]['last_attempt'] = datetime.now()

def is_safe_url(target):
    """فحص أمان الرابط للإعادة التوجيه"""
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# Context processor for templates
@auth_bp.app_context_processor
def inject_user_roles():
    """حقن أدوار المستخدمين في القوالب"""
    return {'UserRole': UserRole}

# Error handlers
@auth_bp.errorhandler(401)
def unauthorized(error):
    """معالج خطأ عدم التصريح"""
    flash('يرجى تسجيل الدخول للوصول لهذه الصفحة', 'warning')
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(403)
def forbidden(error):
    """معالج خطأ الحظر"""
    flash('غير مصرح لك بالوصول لهذه الصفحة', 'error')
    return redirect(url_for('dashboard.index'))