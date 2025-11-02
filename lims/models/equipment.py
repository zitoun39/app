# Equipment Model - نموذج الأجهزة
# Laboratory equipment and calibration management

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from enum import Enum
import json

# Import shared db instance from __init__.py
from . import db

class EquipmentStatus(Enum):
    """حالات الجهاز"""
    ACTIVE = 'active'             # نشط
    INACTIVE = 'inactive'         # غير نشط
    MAINTENANCE = 'maintenance'   # تحت الصيانة
    CALIBRATION = 'calibration'   # تحت المعايرة
    OUT_OF_ORDER = 'out_of_order' # معطل
    RETIRED = 'retired'           # متقاعد

class CalibrationType(Enum):
    """أنواع المعايرة"""
    INITIAL = 'initial'           # معايرة أولية
    PERIODIC = 'periodic'         # معايرة دورية
    VERIFICATION = 'verification' # تحقق
    ADJUSTMENT = 'adjustment'     # تعديل
    REPAIR = 'repair'            # إصلاح

class CalibrationStatus(Enum):
    """حالات المعايرة"""
    SCHEDULED = 'scheduled'       # مجدولة
    IN_PROGRESS = 'in_progress'   # قيد التنفيذ
    COMPLETED = 'completed'       # مكتملة
    FAILED = 'failed'            # فاشلة
    OVERDUE = 'overdue'          # متأخرة

class Equipment(db.Model):
    """نموذج الأجهزة"""
    
    __tablename__ = 'equipment'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # رمز الجهاز
    name = db.Column(db.String(200), nullable=False)  # اسم الجهاز
    name_ar = db.Column(db.String(200))  # الاسم بالعربية
    
    # Equipment Details
    manufacturer = db.Column(db.String(200))  # الشركة المصنعة
    model = db.Column(db.String(200))  # الطراز
    serial_number = db.Column(db.String(200), unique=True)  # الرقم التسلسلي
    
    # Technical Specifications
    specifications = db.Column(db.JSON)  # المواصفات التقنية
    measurement_range = db.Column(db.String(200))  # مدى القياس
    accuracy = db.Column(db.String(100))  # الدقة
    precision = db.Column(db.String(100))  # الضبط
    
    # Location and Assignment
    location = db.Column(db.String(200))  # الموقع
    laboratory_section = db.Column(db.String(100))  # قسم المختبر
    responsible_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # المسؤول
    
    # Status and Condition
    status = db.Column(db.Enum(EquipmentStatus), default=EquipmentStatus.ACTIVE, nullable=False)
    condition_notes = db.Column(db.Text)  # ملاحظات الحالة
    
    # Purchase and Warranty
    purchase_date = db.Column(db.Date)  # تاريخ الشراء
    purchase_cost = db.Column(db.Float)  # تكلفة الشراء
    supplier = db.Column(db.String(200))  # المورد
    warranty_expiry = db.Column(db.Date)  # انتهاء الضمان
    
    # Calibration Schedule
    calibration_interval_days = db.Column(db.Integer, default=365)  # فترة المعايرة بالأيام
    last_calibration_date = db.Column(db.Date)  # آخر معايرة
    next_calibration_date = db.Column(db.Date)  # المعايرة القادمة
    calibration_certificate = db.Column(db.String(500))  # شهادة المعايرة
    
    # Maintenance
    last_maintenance_date = db.Column(db.Date)  # آخر صيانة
    maintenance_interval_days = db.Column(db.Integer, default=180)  # فترة الصيانة
    next_maintenance_date = db.Column(db.Date)  # الصيانة القادمة
    
    # Usage Tracking
    usage_hours = db.Column(db.Float, default=0.0)  # ساعات الاستخدام
    sample_count = db.Column(db.Integer, default=0)  # عدد العينات
    
    # Quality Control
    is_calibrated = db.Column(db.Boolean, default=False)  # معاير
    calibration_valid = db.Column(db.Boolean, default=False)  # المعايرة صالحة
    
    # Parameters and Methods
    supported_parameters = db.Column(db.JSON)  # المعاملات المدعومة
    standard_methods = db.Column(db.JSON)  # الطرق المعيارية
    
    # Documentation
    manual_file = db.Column(db.String(500))  # دليل التشغيل
    sop_file = db.Column(db.String(500))  # إجراءات التشغيل المعيارية
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (commented out to avoid circular imports)
    # responsible_user = db.relationship('User', backref='managed_equipment')
    # calibrations = db.relationship('Calibration', backref='equipment', lazy='dynamic')
    # results = db.relationship('Result', backref='equipment', lazy='dynamic')
    
    def __init__(self, code, name, **kwargs):
        self.code = code
        self.name = name
        
        # Set other attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Calculate initial calibration date
        if self.calibration_interval_days and not self.next_calibration_date:
            self.calculate_next_calibration()
    
    @property
    def is_calibration_due(self):
        """هل المعايرة مستحقة؟"""
        if not self.next_calibration_date:
            return True
        return datetime.now().date() >= self.next_calibration_date
    
    @property
    def is_calibration_overdue(self):
        """هل المعايرة متأخرة؟"""
        if not self.next_calibration_date:
            return True
        return datetime.now().date() > self.next_calibration_date
    
    @property
    def days_until_calibration(self):
        """الأيام المتبقية للمعايرة"""
        if not self.next_calibration_date:
            return 0
        delta = self.next_calibration_date - datetime.now().date()
        return delta.days
    
    @property
    def is_maintenance_due(self):
        """هل الصيانة مستحقة؟"""
        if not self.next_maintenance_date:
            return True
        return datetime.now().date() >= self.next_maintenance_date
    
    @property
    def calibration_status_text(self):
        """نص حالة المعايرة"""
        if not self.is_calibrated:
            return "غير معاير"
        elif self.is_calibration_overdue:
            return "متأخرة"
        elif self.is_calibration_due:
            return "مستحقة"
        else:
            return "صالحة"
    
    def calculate_next_calibration(self):
        """حساب موعد المعايرة القادمة"""
        if self.last_calibration_date and self.calibration_interval_days:
            self.next_calibration_date = self.last_calibration_date + timedelta(days=self.calibration_interval_days)
        elif self.calibration_interval_days:
            # If no previous calibration, schedule from today
            self.next_calibration_date = datetime.now().date() + timedelta(days=self.calibration_interval_days)
    
    def calculate_next_maintenance(self):
        """حساب موعد الصيانة القادمة"""
        if self.last_maintenance_date and self.maintenance_interval_days:
            self.next_maintenance_date = self.last_maintenance_date + timedelta(days=self.maintenance_interval_days)
        elif self.maintenance_interval_days:
            self.next_maintenance_date = datetime.now().date() + timedelta(days=self.maintenance_interval_days)
    
    def record_calibration(self, calibration_date, certificate_number=None, performed_by=None):
        """تسجيل معايرة جديدة"""
        self.last_calibration_date = calibration_date
        self.is_calibrated = True
        self.calibration_valid = True
        
        if certificate_number:
            self.calibration_certificate = certificate_number
        
        # Calculate next calibration
        self.calculate_next_calibration()
        
        # Create calibration record
        calibration = Calibration(
            equipment_id=self.id,
            calibration_date=calibration_date,
            calibration_type=CalibrationType.PERIODIC,
            performed_by=performed_by,
            certificate_number=certificate_number,
            status=CalibrationStatus.COMPLETED
        )
        
        db.session.add(calibration)
        db.session.commit()
        
        return calibration
    
    def record_maintenance(self, maintenance_date, description, performed_by=None):
        """تسجيل صيانة"""
        self.last_maintenance_date = maintenance_date
        self.calculate_next_maintenance()
        
        # Update condition notes
        note = f"صيانة {maintenance_date}: {description}"
        if self.condition_notes:
            self.condition_notes = note + "\n" + self.condition_notes
        else:
            self.condition_notes = note
        
        db.session.commit()
    
    def update_usage(self, hours=None, samples=None):
        """تحديث الاستخدام"""
        if hours:
            self.usage_hours += hours
        
        if samples:
            self.sample_count += samples
        
        db.session.commit()
    
    def set_out_of_order(self, reason):
        """تعطيل الجهاز"""
        self.status = EquipmentStatus.OUT_OF_ORDER
        self.calibration_valid = False
        
        note = f"معطل {datetime.now().date()}: {reason}"
        if self.condition_notes:
            self.condition_notes = note + "\n" + self.condition_notes
        else:
            self.condition_notes = note
        
        db.session.commit()
    
    def return_to_service(self, notes=None):
        """إعادة تشغيل الجهاز"""
        self.status = EquipmentStatus.ACTIVE
        
        if notes:
            note = f"عودة للخدمة {datetime.now().date()}: {notes}"
            if self.condition_notes:
                self.condition_notes = note + "\n" + self.condition_notes
            else:
                self.condition_notes = note
        
        db.session.commit()
    
    def get_calibration_history(self, limit=10):
        """تاريخ المعايرات"""
        return self.calibrations.order_by(Calibration.calibration_date.desc()).limit(limit).all()
    
    def get_recent_results(self, days=30, limit=50):
        """النتائج الحديثة"""
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.results.filter(
            Result.measurement_date >= cutoff_date
        ).order_by(Result.measurement_date.desc()).limit(limit).all()
    
    def to_dict(self, include_details=False):
        """تحويل إلى قاموس"""
        data = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'name_ar': self.name_ar,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'status': self.status.value,
            'location': self.location,
            'is_calibrated': self.is_calibrated,
            'calibration_valid': self.calibration_valid,
            'calibration_status': self.calibration_status_text,
            'days_until_calibration': self.days_until_calibration,
            'is_calibration_due': self.is_calibration_due,
            'is_maintenance_due': self.is_maintenance_due
        }
        
        if include_details:
            data.update({
                'serial_number': self.serial_number,
                'specifications': self.specifications,
                'measurement_range': self.measurement_range,
                'accuracy': self.accuracy,
                'precision': self.precision,
                'laboratory_section': self.laboratory_section,
                'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
                'last_calibration_date': self.last_calibration_date.isoformat() if self.last_calibration_date else None,
                'next_calibration_date': self.next_calibration_date.isoformat() if self.next_calibration_date else None,
                'usage_hours': self.usage_hours,
                'sample_count': self.sample_count,
                'supported_parameters': self.supported_parameters,
                'condition_notes': self.condition_notes,
                'responsible_user': self.responsible_user.full_name if self.responsible_user else None
            })
        
        return data
    
    @classmethod
    def get_calibration_due(cls, days_ahead=30):
        """الأجهزة المستحقة للمعايرة"""
        cutoff_date = datetime.now().date() + timedelta(days=days_ahead)
        return cls.query.filter(
            db.or_(
                cls.next_calibration_date <= cutoff_date,
                cls.next_calibration_date.is_(None)
            )
        ).filter(cls.status != EquipmentStatus.RETIRED).all()
    
    @classmethod
    def get_maintenance_due(cls, days_ahead=7):
        """الأجهزة المستحقة للصيانة"""
        cutoff_date = datetime.now().date() + timedelta(days=days_ahead)
        return cls.query.filter(
            db.or_(
                cls.next_maintenance_date <= cutoff_date,
                cls.next_maintenance_date.is_(None)
            )
        ).filter(cls.status != EquipmentStatus.RETIRED).all()
    
    def __repr__(self):
        return f'<Equipment {self.code}: {self.name}>'

class Calibration(db.Model):
    """نموذج المعايرات"""
    
    __tablename__ = 'calibrations'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False, index=True)
    
    # Calibration Information
    calibration_date = db.Column(db.Date, nullable=False)
    calibration_type = db.Column(db.Enum(CalibrationType), nullable=False)
    status = db.Column(db.Enum(CalibrationStatus), default=CalibrationStatus.SCHEDULED)
    
    # Certificate and Documentation
    certificate_number = db.Column(db.String(200))
    certificate_file = db.Column(db.String(500))  # ملف الشهادة
    calibration_report = db.Column(db.String(500))  # تقرير المعايرة
    
    # Calibration Details
    calibration_points = db.Column(db.JSON)  # نقاط المعايرة
    reference_standards = db.Column(db.JSON)  # المعايير المرجعية
    environmental_conditions = db.Column(db.JSON)  # الظروف البيئية
    
    # Results
    measurement_uncertainty = db.Column(db.Float)  # عدم اليقين
    accuracy_achieved = db.Column(db.String(100))  # الدقة المحققة
    calibration_results = db.Column(db.JSON)  # نتائج المعايرة
    
    # Personnel
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # منفذ المعايرة
    calibration_lab = db.Column(db.String(200))  # مختبر المعايرة
    technician_name = db.Column(db.String(200))  # اسم الفني
    
    # Validity
    valid_until = db.Column(db.Date)  # صالحة حتى
    next_calibration_due = db.Column(db.Date)  # المعايرة القادمة
    
    # Cost
    calibration_cost = db.Column(db.Float)  # تكلفة المعايرة
    
    # Comments
    comments = db.Column(db.Text)
    recommendations = db.Column(db.Text)  # التوصيات
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    performed_by_user = db.relationship('User', backref='performed_calibrations')
    
    def __init__(self, equipment_id, calibration_date, calibration_type, **kwargs):
        self.equipment_id = equipment_id
        self.calibration_date = calibration_date
        self.calibration_type = calibration_type
        
        # Set other attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def is_valid(self):
        """هل المعايرة صالحة؟"""
        if not self.valid_until:
            return False
        return datetime.now().date() <= self.valid_until
    
    @property
    def days_remaining(self):
        """الأيام المتبقية"""
        if not self.valid_until:
            return 0
        delta = self.valid_until - datetime.now().date()
        return max(0, delta.days)
    
    def complete_calibration(self, results, uncertainty=None, comments=None):
        """إكمال المعايرة"""
        self.status = CalibrationStatus.COMPLETED
        self.calibration_results = results
        
        if uncertainty:
            self.measurement_uncertainty = uncertainty
        
        if comments:
            self.comments = comments
        
        # Update equipment calibration status
        equipment = Equipment.query.get(self.equipment_id)
        if equipment:
            equipment.last_calibration_date = self.calibration_date
            equipment.is_calibrated = True
            equipment.calibration_valid = True
            equipment.calculate_next_calibration()
        
        db.session.commit()
    
    def fail_calibration(self, reason):
        """فشل المعايرة"""
        self.status = CalibrationStatus.FAILED
        self.comments = f"فشلت المعايرة: {reason}"
        
        # Update equipment status
        equipment = Equipment.query.get(self.equipment_id)
        if equipment:
            equipment.calibration_valid = False
            equipment.status = EquipmentStatus.OUT_OF_ORDER
        
        db.session.commit()
    
    def to_dict(self):
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            'equipment_code': self.equipment.code,
            'equipment_name': self.equipment.name,
            'calibration_date': self.calibration_date.isoformat(),
            'calibration_type': self.calibration_type.value,
            'status': self.status.value,
            'certificate_number': self.certificate_number,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_valid': self.is_valid,
            'days_remaining': self.days_remaining,
            'performed_by': self.performed_by_user.full_name if self.performed_by_user else None,
            'calibration_lab': self.calibration_lab,
            'measurement_uncertainty': self.measurement_uncertainty,
            'calibration_cost': self.calibration_cost,
            'comments': self.comments,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def get_expiring_soon(cls, days_ahead=30):
        """المعايرات المنتهية قريباً"""
        cutoff_date = datetime.now().date() + timedelta(days=days_ahead)
        return cls.query.filter(
            cls.valid_until <= cutoff_date,
            cls.status == CalibrationStatus.COMPLETED
        ).order_by(cls.valid_until).all()
    
    def __repr__(self):
        return f'<Calibration {self.equipment.code} - {self.calibration_date}>'