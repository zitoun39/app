# User Model - نموذج المستخدم
# User authentication and authorization model

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
import warnings

# Import shared db instance from __init__.py
from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
import warnings

class UserRole(Enum):
    """أدوار المستخدمين في النظام"""
    ADMIN = 'admin'              # مدير النظام
    SUPERVISOR = 'supervisor'    # مشرف المختبر
    ANALYST = 'analyst'          # محلل
    VALIDATOR = 'validator'      # مدقق النتائج
    VIEWER = 'viewer'           # مشاهد فقط

class User(UserMixin, db.Model):
    """نموذج المستخدم - User Model"""
    
    __tablename__ = 'users'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # User Information
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    
    # Role and Permissions
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Laboratory Information
    laboratory_id = db.Column(db.String(20))  # معرف المختبر
    department = db.Column(db.String(100))    # القسم
    position = db.Column(db.String(100))      # المنصب
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Relationships (will be defined after all models are loaded)
    # samples = db.relationship('Sample', backref='created_by_user', lazy='dynamic')
    # results = db.relationship('Result', backref='entered_by_user', lazy='dynamic')
    
    def __init__(self, username, email, password, first_name, last_name, role=UserRole.VIEWER):
        self.username = username
        self.email = email
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
    
    def set_password(self, password):
        """تشفير كلمة المرور"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """التحقق من كلمة المرور"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """الاسم الكامل"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_admin(self):
        """هل المستخدم مدير؟"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_supervisor(self):
        """هل المستخدم مشرف؟"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERVISOR]
    
    @property
    def can_create_samples(self):
        """هل يمكن للمستخدم إنشاء عينات؟"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ANALYST]
    
    @property
    def can_enter_results(self):
        """هل يمكن للمستخدم إدخال النتائج؟"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ANALYST]
    
    @property
    def can_validate_results(self):
        """هل يمكن للمستخدم اعتماد النتائج؟"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VALIDATOR]
    
    @property
    def can_generate_reports(self):
        """هل يمكن للمستخدم إنشاء التقارير؟"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VALIDATOR]
    
    @property
    def can_manage_users(self):
        """هل يمكن للمستخدم إدارة المستخدمين؟"""
        return self.role == UserRole.ADMIN
    
    def is_account_locked(self):
        """هل الحساب مقفل؟"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False
    
    def lock_account(self, duration_minutes=30):
        """قفل الحساب لفترة محددة"""
        from datetime import timedelta
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        db.session.commit()
    
    def unlock_account(self):
        """إلغاء قفل الحساب"""
        self.locked_until = None
        self.failed_login_attempts = 0
        db.session.commit()
    
    def record_login_attempt(self, success=True):
        """تسجيل محاولة تسجيل الدخول"""
        if success:
            self.failed_login_attempts = 0
            self.last_login = datetime.utcnow()
        else:
            self.failed_login_attempts += 1
            # قفل الحساب بعد 5 محاولات فاشلة
            if self.failed_login_attempts >= 5:
                self.lock_account()
        
        db.session.commit()
    
    def get_permissions(self):
        """الحصول على قائمة الصلاحيات"""
        permissions = ['view_samples', 'view_results']
        
        if self.can_create_samples:
            permissions.extend(['create_samples', 'edit_samples'])
        
        if self.can_enter_results:
            permissions.extend(['enter_results', 'edit_results'])
        
        if self.can_validate_results:
            permissions.extend(['validate_results', 'approve_results'])
        
        if self.can_generate_reports:
            permissions.extend(['generate_reports', 'export_data'])
        
        if self.can_manage_users:
            permissions.extend(['manage_users', 'system_settings'])
        
        return permissions
    
    def to_dict(self):
        """تحويل إلى قاموس للـ JSON"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role.value,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'laboratory_id': self.laboratory_id,
            'department': self.department,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'permissions': self.get_permissions()
        }
    
    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'

# User Session Model for tracking active sessions
class UserSession(db.Model):
    """نموذج جلسات المستخدم"""
    
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(255), primary_key=True)  # Session ID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45))  # IPv4/IPv6
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref='sessions')
    
    def is_expired(self, timeout_minutes=120):
        """هل انتهت صلاحية الجلسة؟"""
        from datetime import timedelta
        if not self.last_activity:
            return True
        
        expiry_time = self.last_activity + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiry_time
    
    def update_activity(self):
        """تحديث آخر نشاط"""
        self.last_activity = datetime.utcnow()
        db.session.commit()
    
    def terminate(self):
        """إنهاء الجلسة"""
        self.is_active = False
        db.session.commit()