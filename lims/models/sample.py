# Sample Model - نموذج العينة
# Water sample management model

from datetime import datetime, date
from enum import Enum
import re

from extensions import db

class SampleStatus(Enum):
    """حالات العينة"""
    REGISTERED = 'registered'        # مسجلة
    IN_PROGRESS = 'in_progress'     # قيد التحليل
    COMPLETED = 'completed'         # مكتملة
    VALIDATED = 'validated'         # معتمدة
    REPORTED = 'reported'           # تم إصدار التقرير
    CANCELLED = 'cancelled'         # ملغية

class SampleType(db.Model):
    """أنواع العينات"""
    
    __tablename__ = 'sample_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    name_ar = db.Column(db.String(100), nullable=False)  # الاسم بالعربية
    description = db.Column(db.Text)
    code = db.Column(db.String(10), unique=True)  # رمز النوع
    
    # Default parameters for this sample type
    default_parameters = db.Column(db.JSON)  # قائمة معرفات المعايير الافتراضية
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    samples = db.relationship('Sample', backref='sample_type_ref', lazy='dynamic')
    
    def __repr__(self):
        return f'<SampleType {self.name}>'

class Sample(db.Model):
    """نموذج العينة الرئيسي"""
    
    __tablename__ = 'samples'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Sample Identification
    sample_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    internal_id = db.Column(db.String(50))  # معرف داخلي إضافي
    
    # Sample Information
    sample_type_id = db.Column(db.Integer, db.ForeignKey('sample_types.id'), nullable=False)
    description = db.Column(db.Text)
    
    # Collection Information
    collection_date = db.Column(db.Date, nullable=False, default=date.today)
    collection_time = db.Column(db.Time)
    collection_point = db.Column(db.String(200))  # نقطة الجمع
    collector_name = db.Column(db.String(100))    # اسم جامع العينة
    
    # Location Information
    municipality = db.Column(db.String(100))      # البلدية
    wilaya = db.Column(db.String(100))           # الولاية
    coordinates = db.Column(db.String(100))       # الإحداثيات GPS
    
    # Client Information
    client_name = db.Column(db.String(200))
    client_address = db.Column(db.Text)
    client_phone = db.Column(db.String(20))
    client_email = db.Column(db.String(120))
    
    # Sample Characteristics
    temperature = db.Column(db.Float)             # درجة الحرارة عند الجمع
    ph_field = db.Column(db.Float)               # pH في الموقع
    conductivity_field = db.Column(db.Float)      # التوصيلية في الموقع
    
    # Storage and Handling
    storage_conditions = db.Column(db.String(200))  # ظروف التخزين
    preservation_method = db.Column(db.String(200)) # طريقة الحفظ
    container_type = db.Column(db.String(100))      # نوع الحاوية
    
    # Status and Workflow
    status = db.Column(db.Enum(SampleStatus), default=SampleStatus.REGISTERED, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # normal, high, urgent
    
    # Analysis Information
    analysis_start_date = db.Column(db.DateTime)
    analysis_end_date = db.Column(db.DateTime)
    expected_completion = db.Column(db.Date)
    
    # Quality Control
    is_duplicate = db.Column(db.Boolean, default=False)
    original_sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'))
    is_blank = db.Column(db.Boolean, default=False)
    is_control = db.Column(db.Boolean, default=False)
    
    # User Tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    validated_at = db.Column(db.DateTime)
    
    # Comments and Notes
    comments = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # ملاحظات داخلية
    
    # Relationships (commented out to avoid circular imports)
    # results = db.relationship('Result', backref='sample', lazy='dynamic', cascade='all, delete-orphan')
    # duplicates = db.relationship('Sample', backref=db.backref('original_sample', remote_side=[id]))
    
    def __init__(self, sample_type_id, collection_date=None, **kwargs):
        self.sample_type_id = sample_type_id
        self.collection_date = collection_date or date.today()
        
        # Generate sample ID if not provided
        if 'sample_id' not in kwargs:
            self.sample_id = self.generate_sample_id()
        
        # Set other attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def generate_sample_id(self):
        """توليد معرف العينة التلقائي"""
        # Format: ADE + YEAR + sequential number
        # Example: ADE2024001, ADE2024002, etc.
        
        current_year = datetime.now().year
        year_str = str(current_year)
        
        # Find the last sample ID for this year
        last_sample = db.session.query(Sample).filter(
            Sample.sample_id.like(f'ADE{year_str}%')
        ).order_by(Sample.sample_id.desc()).first()
        
        if last_sample:
            # Extract the sequential number
            match = re.search(r'ADE(\d{4})(\d{3})', last_sample.sample_id)
            if match:
                last_number = int(match.group(2))
                new_number = last_number + 1
            else:
                new_number = 1
        else:
            new_number = 1
        
        return f'ADE{year_str}{new_number:03d}'
    
    @property
    def is_overdue(self):
        """هل العينة متأخرة؟"""
        if not self.expected_completion:
            return False
        return date.today() > self.expected_completion
    
    @property
    def days_since_collection(self):
        """عدد الأيام منذ جمع العينة"""
        return (date.today() - self.collection_date).days
    
    @property
    def analysis_duration(self):
        """مدة التحليل بالساعات"""
        if self.analysis_start_date and self.analysis_end_date:
            duration = self.analysis_end_date - self.analysis_start_date
            return duration.total_seconds() / 3600  # Convert to hours
        return None
    
    @property
    def completion_percentage(self):
        """نسبة اكتمال التحليل"""
        total_results = self.results.count()
        if total_results == 0:
            return 0
        
        completed_results = self.results.filter_by(status='completed').count()
        return (completed_results / total_results) * 100
    
    @property
    def conformity_status(self):
        """حالة المطابقة العامة للعينة"""
        results = self.results.filter_by(status='completed').all()
        if not results:
            return 'pending'
        
        non_conforming = any(not result.is_conforming for result in results)
        return 'non_conforming' if non_conforming else 'conforming'
    
    def get_result_by_parameter(self, parameter_id):
        """الحصول على نتيجة معاير محدد"""
        return self.results.filter_by(parameter_id=parameter_id).first()
    
    def start_analysis(self, user_id):
        """بدء التحليل"""
        self.status = SampleStatus.IN_PROGRESS
        self.analysis_start_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def complete_analysis(self, user_id):
        """إكمال التحليل"""
        self.status = SampleStatus.COMPLETED
        self.analysis_end_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def validate_sample(self, user_id):
        """اعتماد العينة"""
        self.status = SampleStatus.VALIDATED
        self.validated_by = user_id
        self.validated_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def generate_report(self, user_id):
        """إنشاء التقرير"""
        self.status = SampleStatus.REPORTED
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def cancel_sample(self, reason, user_id):
        """إلغاء العينة"""
        self.status = SampleStatus.CANCELLED
        self.comments = f"ملغية: {reason}" + (f"\n{self.comments}" if self.comments else "")
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def create_duplicate(self, user_id):
        """إنشاء عينة مكررة"""
        duplicate = Sample(
            sample_type_id=self.sample_type_id,
            collection_date=self.collection_date,
            collection_time=self.collection_time,
            collection_point=self.collection_point,
            municipality=self.municipality,
            wilaya=self.wilaya,
            is_duplicate=True,
            original_sample_id=self.id,
            created_by=user_id
        )
        
        # Generate duplicate sample ID
        duplicate.sample_id = f"{self.sample_id}-DUP"
        
        db.session.add(duplicate)
        db.session.commit()
        return duplicate
    
    def to_dict(self, include_results=False):
        """تحويل إلى قاموس للـ JSON"""
        data = {
            'id': self.id,
            'sample_id': self.sample_id,
            'sample_type': self.sample_type_ref.name if self.sample_type_ref else None,
            'collection_date': self.collection_date.isoformat() if self.collection_date else None,
            'collection_point': self.collection_point,
            'municipality': self.municipality,
            'wilaya': self.wilaya,
            'status': self.status.value,
            'priority': self.priority,
            'conformity_status': self.conformity_status,
            'completion_percentage': self.completion_percentage,
            'days_since_collection': self.days_since_collection,
            'is_overdue': self.is_overdue,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_results:
            data['results'] = [result.to_dict() for result in self.results]
        
        return data
    
    def __repr__(self):
        return f'<Sample {self.sample_id} ({self.status.value})>'

# Sample Chain of Custody Model
class SampleCustody(db.Model):
    """سلسلة حفظ العينة"""
    
    __tablename__ = 'sample_custody'
    
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), nullable=False)
    
    # Custody Information
    transferred_from = db.Column(db.Integer, db.ForeignKey('users.id'))
    transferred_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transfer_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Transfer Details
    purpose = db.Column(db.String(200))  # غرض النقل
    condition = db.Column(db.String(200))  # حالة العينة
    comments = db.Column(db.Text)
    
    # Relationships
    sample = db.relationship('Sample', backref='custody_chain')
    from_user = db.relationship('User', foreign_keys=[transferred_from])
    to_user = db.relationship('User', foreign_keys=[transferred_to])
    
    def __repr__(self):
        return f'<SampleCustody {self.sample_id} -> {self.to_user.username}>'