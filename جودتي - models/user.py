"""
نموذج المستخدم
"""

from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    """نموذج المستخدمين"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, default='viewer')
    phone = db.Column(db.String(20))
    signature = db.Column(db.Text)  # التوقيع الرقمي
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # العلاقات
    collected_samples = db.relationship('Sample', foreign_keys='Sample.collector_id', backref='collector')
    analyzed_samples = db.relationship('Sample', foreign_keys='Sample.analyst_id', backref='analyst')
    validated_samples = db.relationship('Sample', foreign_keys='Sample.validator_id', backref='validator')
    created_samples = db.relationship('Sample', foreign_keys='Sample.created_by', backref='creator')
    
    def set_password(self, password):
        """تشفير كلمة المرور"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """التحقق من كلمة المرور"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """تحديث آخر تسجيل دخول"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @property
    def role_ar(self):
        """دور المستخدم بالعربية"""
        roles = {
            'admin': 'مدير النظام',
            'supervisor': 'رئيس المخبر',
            'analyst': 'محلل',
            'validator': 'مراجع',
            'viewer': 'مشاهد'
        }
        return roles.get(self.role, self.role)
    
    def can(self, action):
        """التحقق من صلاحية المستخدم"""
        permissions = {
            'admin': ['create', 'read', 'update', 'delete', 'validate', 'configure'],
            'supervisor': ['create', 'read', 'update', 'validate'],
            'analyst': ['create', 'read', 'update'],
            'validator': ['read', 'validate'],
            'viewer': ['read']
        }
        return action in permissions.get(self.role, [])
    
    def __repr__(self):
        return f'<User {self.username}>'