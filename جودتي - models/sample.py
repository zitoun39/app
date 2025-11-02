"""
نموذج العينات
"""

from app import db
from datetime import datetime
from sqlalchemy import event


class SampleType(db.Model):
    """أنواع العينات"""
    
    __tablename__ = 'sample_types'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    name_fr = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    samples = db.relationship('Sample', backref='sample_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<SampleType {self.code}>'


class Sample(db.Model):
    """العينات"""
    
    __tablename__ = 'samples'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # معلومات الأخذ
    collection_date = db.Column(db.Date, nullable=False, index=True)
    reception_datetime = db.Column(db.DateTime, default=datetime.utcnow)
    sample_type_id = db.Column(db.Integer, db.ForeignKey('sample_types.id'), nullable=False)
    
    # الموقع
    location_name = db.Column(db.String(200), nullable=False)
    commune = db.Column(db.String(100))
    wilaya = db.Column(db.String(100), default='سطيف')
    
    # الشخص الذي جمع العينة
    collector_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # معلومات إضافية
    temperature = db.Column(db.Numeric(4, 2))
    weather_conditions = db.Column(db.Text)
    transport_conditions = db.Column(db.Text)
    
    # نوع التحليل المطلوب
    analysis_type = db.Column(db.String(30), nullable=False, default='complete')
    
    # الحالة
    status = db.Column(db.String(20), default='pending', index=True)
    
    # المحلل والمراجع
    analyst_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    validator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    analysis_date = db.Column(db.Date)
    validation_date = db.Column(db.Date)
    
    # الملاحظات
    notes = db.Column(db.Text)
    observations = db.Column(db.Text)
    
    # المطابقة
    compliance_status = db.Column(db.String(20))
    
    # التتبع
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    results = db.relationship('Result', backref='sample', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def status_ar(self):
        """الحالة بالعربية"""
        statuses = {
            'pending': 'قيد الانتظار',
            'in_progress': 'قيد التحليل',
            'completed': 'منتهي',
            'archived': 'مؤرشف'
        }
        return statuses.get(self.status, self.status)
    
    @property
    def analysis_type_ar(self):
        """نوع التحليل بالعربية"""
        types = {
            'partial': 'تحليل جزئي',
            'complete': 'تحليل كامل',
            'bacteriological': 'تحليل بكتريولوجي',
            'custom': 'تحليل مخصص'
        }
        return types.get(self.analysis_type, self.analysis_type)
    
    @property
    def compliance_badge(self):
        """شارة المطابقة"""
        if not self.compliance_status:
            return '<span class="badge bg-secondary">لم يحدد</span>'
        
        badges = {
            'compliant': '<span class="badge bg-success">✓ مطابق</span>',
            'warning': '<span class="badge bg-warning">⚠ قريب من الحد</span>',
            'non_compliant': '<span class="badge bg-danger">✗ غير مطابق</span>'
        }
        return badges.get(self.compliance_status, '')
    
    def calculate_compliance(self):
        """حساب حالة المطابقة بناءً على النتائج"""
        if not self.results.count():
            return None
        
        has_non_compliant = False
        has_warning = False
        
        for result in self.results:
            if result.compliance == 'non_compliant':
                has_non_compliant = True
                break
            elif result.compliance == 'warning':
                has_warning = True
        
        if has_non_compliant:
            self.compliance_status = 'non_compliant'
        elif has_warning:
            self.compliance_status = 'warning'
        else:
            self.compliance_status = 'compliant'
        
        return self.compliance_status
    
    def get_required_parameters(self):
        """الحصول على المعايير المطلوبة حسب نوع التحليل"""
        from models.parameter import Parameter
        
        query = Parameter.query.filter_by(active=True)
        
        if self.analysis_type == 'partial':
            query = query.filter_by(in_partial=True)
        elif self.analysis_type == 'complete':
            query = query.filter_by(in_complete=True)
        elif self.analysis_type == 'bacteriological':
            query = query.filter_by(in_bacteriological=True)
        
        return query.order_by(Parameter.display_order).all()
    
    def __repr__(self):
        return f'<Sample {self.code}>'


class CodeSequence(db.Model):
    """تسلسل أكواد العينات"""
    
    __tablename__ = 'code_sequences'
    
    id = db.Column(db.Integer, primary_key=True)
    sample_type_id = db.Column(db.Integer, db.ForeignKey('sample_types.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    last_sequence = db.Column(db.Integer, default=0)
    
    __table_args__ = (
        db.UniqueConstraint('sample_type_id', 'year', name='uq_sample_type_year'),
    )
    
    @staticmethod
    def get_next_code(sample_type_id, year=None):
        """الحصول على الكود التالي"""
        if year is None:
            year = datetime.now().year
        
        # البحث عن التسلسل أو إنشاءه
        sequence = CodeSequence.query.filter_by(
            sample_type_id=sample_type_id,
            year=year
        ).first()
        
        if not sequence:
            sequence = CodeSequence(
                sample_type_id=sample_type_id,
                year=year,
                last_sequence=0
            )
            db.session.add(sequence)
        
        # زيادة التسلسل
        sequence.last_sequence += 1
        db.session.commit()
        
        # إنشاء الكود
        sample_type = SampleType.query.get(sample_type_id)
        code = f"{sample_type.code}{str(year)[-2:]}-{sequence.last_sequence:04d}"
        
        return code
    
    def __repr__(self):
        return f'<CodeSequence {self.year}:{self.last_sequence}>'
        