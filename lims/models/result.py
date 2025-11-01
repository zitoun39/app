# Result Model - نموذج النتائج
# Laboratory test results model

from datetime import datetime
from enum import Enum
import json

from extensions import db

class ResultStatus(Enum):
    """حالات النتيجة"""
    PENDING = 'pending'           # في الانتظار
    IN_PROGRESS = 'in_progress'   # قيد التحليل
    COMPLETED = 'completed'       # مكتملة
    VALIDATED = 'validated'       # معتمدة
    REJECTED = 'rejected'         # مرفوضة
    CANCELLED = 'cancelled'       # ملغية

class QualityFlag(Enum):
    """علامات الجودة"""
    GOOD = 'good'                 # جيدة
    QUESTIONABLE = 'questionable' # مشكوك فيها
    BAD = 'bad'                   # سيئة
    ESTIMATED = 'estimated'       # مقدرة
    BELOW_DETECTION = 'below_detection'  # أقل من حد الكشف

class Result(db.Model):
    """نموذج النتائج الرئيسي"""
    
    __tablename__ = 'results'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), nullable=False, index=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False, index=True)
    
    # Result Values
    value = db.Column(db.Float)  # القيمة الرقمية
    text_value = db.Column(db.String(200))  # القيمة النصية (للنتائج النوعية)
    
    # Quality Control
    raw_value = db.Column(db.Float)  # القيمة الخام قبل المعايرة
    corrected_value = db.Column(db.Float)  # القيمة المصححة
    dilution_factor = db.Column(db.Float, default=1.0)  # معامل التخفيف
    
    # Measurement Information
    measurement_date = db.Column(db.DateTime, default=datetime.utcnow)
    measurement_time = db.Column(db.Time)
    analyst_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Equipment and Method
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    method_used = db.Column(db.String(200))  # الطريقة المستخدمة
    
    # Status and Quality
    status = db.Column(db.Enum(ResultStatus), default=ResultStatus.PENDING, nullable=False)
    quality_flag = db.Column(db.Enum(QualityFlag), default=QualityFlag.GOOD)
    
    # Conformity Assessment
    is_conforming = db.Column(db.Boolean)  # مطابق للمرسوم 11-219
    conformity_details = db.Column(db.JSON)  # تفاصيل المطابقة
    
    # Uncertainty and Statistics
    uncertainty = db.Column(db.Float)  # عدم اليقين
    standard_deviation = db.Column(db.Float)  # الانحراف المعياري
    coefficient_variation = db.Column(db.Float)  # معامل التباين
    
    # Replicates (for multiple measurements)
    replicate_number = db.Column(db.Integer, default=1)  # رقم التكرار
    replicate_values = db.Column(db.JSON)  # قيم التكرارات
    
    # Detection and Quantification
    is_below_detection_limit = db.Column(db.Boolean, default=False)
    is_below_quantification_limit = db.Column(db.Boolean, default=False)
    
    # User Tracking
    entered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    validated_at = db.Column(db.DateTime)
    
    # Comments and Notes
    comments = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # ملاحظات داخلية
    
    # Relationships (commented out to avoid circular imports)
    # analyst = db.relationship('User', foreign_keys=[analyst_id], backref='analyzed_results')
    # entered_by_user = db.relationship('User', foreign_keys=[entered_by], backref='entered_results')
    # validated_by_user = db.relationship('User', foreign_keys=[validated_by], backref='validated_results')
    
    def __init__(self, sample_id, parameter_id, entered_by, **kwargs):
        self.sample_id = sample_id
        self.parameter_id = parameter_id
        self.entered_by = entered_by
        
        # Set other attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def final_value(self):
        """القيمة النهائية (مع التصحيحات)"""
        if self.corrected_value is not None:
            return self.corrected_value
        elif self.value is not None:
            return self.value * (self.dilution_factor or 1.0)
        return None
    
    @property
    def display_value(self):
        """القيمة للعرض (مع معالجة الحالات الخاصة)"""
        if self.is_below_detection_limit:
            return f"< {self.parameter.detection_limit} {self.parameter.unit}"
        elif self.is_below_quantification_limit:
            return f"< {self.parameter.quantification_limit} {self.parameter.unit}"
        elif self.text_value:
            return self.text_value
        elif self.final_value is not None:
            decimal_places = self.parameter.decimal_places or 2
            return f"{self.final_value:.{decimal_places}f} {self.parameter.unit}"
        return "غير محدد"
    
    @property
    def formatted_value(self):
        """القيمة منسقة للتقارير"""
        if self.final_value is None:
            return self.display_value
        
        decimal_places = self.parameter.decimal_places or 2
        formatted = f"{self.final_value:.{decimal_places}f}"
        
        # Add uncertainty if available
        if self.uncertainty:
            formatted += f" ± {self.uncertainty:.{decimal_places}f}"
        
        return f"{formatted} {self.parameter.unit}"
    
    def calculate_conformity(self, standard='decree'):
        """حساب المطابقة"""
        if self.final_value is None:
            return None
        
        conformity = self.parameter.check_conformity(self.final_value, standard)
        
        # Update conformity status
        if conformity:
            self.is_conforming = conformity['conforming']
            self.conformity_details = conformity
            db.session.commit()
        
        return conformity
    
    def add_replicate(self, value):
        """إضافة تكرار جديد"""
        if not self.replicate_values:
            self.replicate_values = []
        
        self.replicate_values.append(value)
        self.replicate_number = len(self.replicate_values)
        
        # Calculate statistics
        self.calculate_statistics()
        
        db.session.commit()
    
    def calculate_statistics(self):
        """حساب الإحصائيات"""
        if not self.replicate_values or len(self.replicate_values) < 2:
            return
        
        import statistics
        
        values = self.replicate_values
        
        # Calculate mean
        self.value = statistics.mean(values)
        
        # Calculate standard deviation
        self.standard_deviation = statistics.stdev(values)
        
        # Calculate coefficient of variation
        if self.value != 0:
            self.coefficient_variation = (self.standard_deviation / abs(self.value)) * 100
        
        # Calculate uncertainty (assuming 95% confidence interval)
        import math
        n = len(values)
        t_value = 2.0  # Approximate t-value for 95% CI
        self.uncertainty = (self.standard_deviation / math.sqrt(n)) * t_value
    
    def validate_result(self, validator_id, comments=None):
        """اعتماد النتيجة"""
        self.status = ResultStatus.VALIDATED
        self.validated_by = validator_id
        self.validated_at = datetime.utcnow()
        
        if comments:
            self.comments = comments
        
        # Recalculate conformity
        self.calculate_conformity()
        
        db.session.commit()
    
    def reject_result(self, validator_id, reason):
        """رفض النتيجة"""
        self.status = ResultStatus.REJECTED
        self.validated_by = validator_id
        self.validated_at = datetime.utcnow()
        self.comments = f"مرفوضة: {reason}"
        
        db.session.commit()
    
    def flag_quality(self, flag, reason=None):
        """وضع علامة جودة"""
        self.quality_flag = flag
        
        if reason:
            note = f"علامة الجودة: {flag.value} - {reason}"
            self.internal_notes = note + (f"\n{self.internal_notes}" if self.internal_notes else "")
        
        db.session.commit()
    
    def get_quality_status(self):
        """حالة الجودة"""
        status = {
            'flag': self.quality_flag.value if self.quality_flag else 'good',
            'conforming': self.is_conforming,
            'below_detection': self.is_below_detection_limit,
            'below_quantification': self.is_below_quantification_limit,
            'has_uncertainty': self.uncertainty is not None,
            'replicate_count': self.replicate_number or 1
        }
        
        # Overall quality assessment
        if self.quality_flag == QualityFlag.BAD or not self.is_conforming:
            status['overall'] = 'poor'
        elif self.quality_flag == QualityFlag.QUESTIONABLE:
            status['overall'] = 'questionable'
        else:
            status['overall'] = 'good'
        
        return status
    
    def to_dict(self, include_details=False):
        """تحويل إلى قاموس للـ JSON"""
        data = {
            'id': self.id,
            'sample_id': self.sample_id,
            'parameter_code': self.parameter.code,
            'parameter_name': self.parameter.name_ar,
            'value': self.final_value,
            'display_value': self.display_value,
            'formatted_value': self.formatted_value,
            'unit': self.parameter.unit,
            'status': self.status.value,
            'is_conforming': self.is_conforming,
            'quality_flag': self.quality_flag.value if self.quality_flag else 'good',
            'measurement_date': self.measurement_date.isoformat() if self.measurement_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_details:
            data.update({
                'raw_value': self.raw_value,
                'corrected_value': self.corrected_value,
                'dilution_factor': self.dilution_factor,
                'uncertainty': self.uncertainty,
                'standard_deviation': self.standard_deviation,
                'coefficient_variation': self.coefficient_variation,
                'replicate_values': self.replicate_values,
                'conformity_details': self.conformity_details,
                'quality_status': self.get_quality_status(),
                'comments': self.comments,
                'analyst': self.analyst.full_name if self.analyst else None,
                'validated_by': self.validated_by_user.full_name if self.validated_by_user else None,
                'validated_at': self.validated_at.isoformat() if self.validated_at else None
            })
        
        return data
    
    @classmethod
    def get_by_sample(cls, sample_id, include_pending=True):
        """الحصول على نتائج العينة"""
        query = cls.query.filter_by(sample_id=sample_id)
        
        if not include_pending:
            query = query.filter(cls.status != ResultStatus.PENDING)
        
        return query.order_by(cls.parameter.has(Parameter.sort_order)).all()
    
    @classmethod
    def get_non_conforming_results(cls, date_from=None, date_to=None):
        """الحصول على النتائج غير المطابقة"""
        query = cls.query.filter_by(is_conforming=False)
        
        if date_from:
            query = query.filter(cls.measurement_date >= date_from)
        
        if date_to:
            query = query.filter(cls.measurement_date <= date_to)
        
        return query.order_by(cls.measurement_date.desc()).all()
    
    def __repr__(self):
        return f'<Result {self.sample.sample_id} - {self.parameter.code}: {self.display_value}>'

# Test Result Model for batch testing
class TestResult(db.Model):
    """نموذج نتائج الاختبار المجمعة"""
    
    __tablename__ = 'test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Batch Information
    batch_id = db.Column(db.String(50), nullable=False, index=True)
    test_date = db.Column(db.Date, nullable=False)
    analyst_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Test Details
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    method_used = db.Column(db.String(200))
    
    # Results Data (JSON format for multiple samples)
    results_data = db.Column(db.JSON, nullable=False)
    
    # Quality Control
    control_samples = db.Column(db.JSON)  # نتائج عينات المراقبة
    blank_results = db.Column(db.JSON)    # نتائج العينات الفارغة
    duplicate_results = db.Column(db.JSON)  # نتائج العينات المكررة
    
    # Status
    status = db.Column(db.Enum(ResultStatus), default=ResultStatus.COMPLETED)
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    validated_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyst = db.relationship('User', foreign_keys=[analyst_id])
    parameter = db.relationship('Parameter')
    validator = db.relationship('User', foreign_keys=[validated_by])
    
    def process_results(self):
        """معالجة النتائج وإنشاء سجلات Result منفصلة"""
        if not self.results_data:
            return
        
        for sample_data in self.results_data:
            sample_id = sample_data.get('sample_id')
            value = sample_data.get('value')
            
            if sample_id and value is not None:
                # Create or update Result record
                result = Result.query.filter_by(
                    sample_id=sample_id,
                    parameter_id=self.parameter_id
                ).first()
                
                if not result:
                    result = Result(
                        sample_id=sample_id,
                        parameter_id=self.parameter_id,
                        entered_by=self.analyst_id
                    )
                    db.session.add(result)
                
                # Update result values
                result.value = value
                result.measurement_date = datetime.combine(self.test_date, datetime.now().time())
                result.analyst_id = self.analyst_id
                result.equipment_id = self.equipment_id
                result.method_used = self.method_used
                result.status = ResultStatus.COMPLETED
                
                # Calculate conformity
                result.calculate_conformity()
        
        db.session.commit()
    
    def __repr__(self):
        return f'<TestResult {self.batch_id} - {self.parameter.code}>'