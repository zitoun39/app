# Parameter Model - نموذج المعايير
# Water quality parameters and standards model

from datetime import datetime
from enum import Enum
import json

from extensions import db

class ParameterType(Enum):
    """أنواع المعايير"""
    PHYSICAL = 'physical'           # فيزيائية
    CHEMICAL = 'chemical'           # كيميائية
    BIOLOGICAL = 'biological'       # بيولوجية
    MICROBIOLOGICAL = 'microbiological'  # ميكروبيولوجية
    RADIOLOGICAL = 'radiological'   # إشعاعية

class ParameterCategory(db.Model):
    """فئات المعايير"""
    
    __tablename__ = 'parameter_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    name_ar = db.Column(db.String(100), nullable=False)  # الاسم بالعربية
    description = db.Column(db.Text)
    type = db.Column(db.Enum(ParameterType), nullable=False)
    
    # Display Properties
    color = db.Column(db.String(7), default='#007bff')  # لون الفئة (hex)
    icon = db.Column(db.String(50))  # أيقونة الفئة
    sort_order = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    parameters = db.relationship('Parameter', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<ParameterCategory {self.name}>'

class Parameter(db.Model):
    """نموذج المعايير"""
    
    __tablename__ = 'parameters'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Parameter Information
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    name_ar = db.Column(db.String(200), nullable=False)  # الاسم بالعربية
    description = db.Column(db.Text)
    
    # Category
    category_id = db.Column(db.Integer, db.ForeignKey('parameter_categories.id'), nullable=False)
    
    # Units and Measurement
    unit = db.Column(db.String(50), nullable=False)  # وحدة القياس
    unit_ar = db.Column(db.String(50))  # وحدة القياس بالعربية
    
    # Limits and Standards (Decree 11-219)
    min_limit = db.Column(db.Float)  # الحد الأدنى
    max_limit = db.Column(db.Float)  # الحد الأقصى
    target_value = db.Column(db.Float)  # القيمة المستهدفة
    
    # WHO Standards
    who_min_limit = db.Column(db.Float)
    who_max_limit = db.Column(db.Float)
    who_guideline = db.Column(db.Float)
    
    # ISO Standards
    iso_min_limit = db.Column(db.Float)
    iso_max_limit = db.Column(db.Float)
    iso_standard = db.Column(db.String(50))  # رقم المعيار ISO
    
    # Analysis Information
    analysis_method = db.Column(db.String(200))  # طريقة التحليل
    analysis_method_ar = db.Column(db.String(200))  # طريقة التحليل بالعربية
    equipment_required = db.Column(db.String(200))  # الأجهزة المطلوبة
    
    # Quality Control
    precision = db.Column(db.Float)  # الدقة
    accuracy = db.Column(db.Float)   # الصحة
    detection_limit = db.Column(db.Float)  # حد الكشف
    quantification_limit = db.Column(db.Float)  # حد التقدير
    
    # Calculation and Formula
    calculation_formula = db.Column(db.Text)  # معادلة الحساب
    dependent_parameters = db.Column(db.JSON)  # المعايير التابعة
    
    # Display Properties
    decimal_places = db.Column(db.Integer, default=2)  # عدد المنازل العشرية
    is_calculated = db.Column(db.Boolean, default=False)  # هل يتم حسابه تلقائياً؟
    is_mandatory = db.Column(db.Boolean, default=True)   # هل هو إجباري؟
    is_active = db.Column(db.Boolean, default=True)      # هل هو نشط؟
    
    # Sorting and Grouping
    sort_order = db.Column(db.Integer, default=0)
    group_name = db.Column(db.String(100))  # اسم المجموعة
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    results = db.relationship('Result', backref='parameter', lazy='dynamic')
    
    def __init__(self, code, name, name_ar, unit, category_id, **kwargs):
        self.code = code
        self.name = name
        self.name_ar = name_ar
        self.unit = unit
        self.category_id = category_id
        
        # Set other attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def has_limits(self):
        """هل للمعيار حدود محددة؟"""
        return self.min_limit is not None or self.max_limit is not None
    
    @property
    def limit_range(self):
        """نطاق الحدود المسموحة"""
        if not self.has_limits:
            return None
        
        min_val = self.min_limit if self.min_limit is not None else 'لا يوجد'
        max_val = self.max_limit if self.max_limit is not None else 'لا يوجد'
        
        return f"{min_val} - {max_val} {self.unit}"
    
    def check_conformity(self, value, standard='decree'):
        """فحص مطابقة القيمة للمعايير"""
        if value is None:
            return None
        
        # Choose limits based on standard
        if standard == 'who':
            min_limit = self.who_min_limit
            max_limit = self.who_max_limit
        elif standard == 'iso':
            min_limit = self.iso_min_limit
            max_limit = self.iso_max_limit
        else:  # decree (default)
            min_limit = self.min_limit
            max_limit = self.max_limit
        
        # Check conformity
        conforming = True
        
        if min_limit is not None and value < min_limit:
            conforming = False
        
        if max_limit is not None and value > max_limit:
            conforming = False
        
        return {
            'conforming': conforming,
            'value': value,
            'min_limit': min_limit,
            'max_limit': max_limit,
            'standard': standard,
            'unit': self.unit
        }
    
    def calculate_value(self, input_values):
        """حساب القيمة باستخدام المعادلة"""
        if not self.is_calculated or not self.calculation_formula:
            return None
        
        try:
            # Replace parameter codes with values in formula
            formula = self.calculation_formula
            
            for param_code, value in input_values.items():
                formula = formula.replace(f'{{{param_code}}}', str(value))
            
            # Evaluate the formula safely
            # Note: In production, use a safer evaluation method
            result = eval(formula)
            
            # Round to specified decimal places
            return round(result, self.decimal_places)
            
        except Exception as e:
            print(f"Error calculating parameter {self.code}: {e}")
            return None
    
    def get_reference_values(self):
        """الحصول على القيم المرجعية لجميع المعايير"""
        return {
            'decree_11_219': {
                'min_limit': self.min_limit,
                'max_limit': self.max_limit,
                'target_value': self.target_value
            },
            'who_guidelines': {
                'min_limit': self.who_min_limit,
                'max_limit': self.who_max_limit,
                'guideline': self.who_guideline
            },
            'iso_standards': {
                'min_limit': self.iso_min_limit,
                'max_limit': self.iso_max_limit,
                'standard': self.iso_standard
            }
        }
    
    def get_analysis_info(self):
        """معلومات التحليل"""
        return {
            'method': self.analysis_method,
            'method_ar': self.analysis_method_ar,
            'equipment': self.equipment_required,
            'precision': self.precision,
            'accuracy': self.accuracy,
            'detection_limit': self.detection_limit,
            'quantification_limit': self.quantification_limit
        }
    
    def to_dict(self, include_limits=True):
        """تحويل إلى قاموس للـ JSON"""
        data = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'name_ar': self.name_ar,
            'unit': self.unit,
            'unit_ar': self.unit_ar,
            'category': self.category.name if self.category else None,
            'category_ar': self.category.name_ar if self.category else None,
            'type': self.category.type.value if self.category else None,
            'decimal_places': self.decimal_places,
            'is_calculated': self.is_calculated,
            'is_mandatory': self.is_mandatory,
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }
        
        if include_limits:
            data.update({
                'limits': self.get_reference_values(),
                'analysis_info': self.get_analysis_info(),
                'limit_range': self.limit_range
            })
        
        return data
    
    @classmethod
    def get_by_category(cls, category_id):
        """الحصول على المعايير حسب الفئة"""
        return cls.query.filter_by(category_id=category_id, is_active=True).order_by(cls.sort_order).all()
    
    @classmethod
    def get_mandatory_parameters(cls):
        """الحصول على المعايير الإجبارية"""
        return cls.query.filter_by(is_mandatory=True, is_active=True).order_by(cls.sort_order).all()
    
    @classmethod
    def search_parameters(cls, query):
        """البحث في المعايير"""
        return cls.query.filter(
            db.or_(
                cls.name.contains(query),
                cls.name_ar.contains(query),
                cls.code.contains(query)
            )
        ).filter_by(is_active=True).all()
    
    def __repr__(self):
        return f'<Parameter {self.code}: {self.name}>'

# Parameter Standards Model for different regulations
class ParameterStandard(db.Model):
    """معايير المعايير حسب اللوائح المختلفة"""
    
    __tablename__ = 'parameter_standards'
    
    id = db.Column(db.Integer, primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False)
    
    # Standard Information
    standard_name = db.Column(db.String(100), nullable=False)  # اسم المعيار
    standard_code = db.Column(db.String(50))  # رمز المعيار
    country = db.Column(db.String(50))  # البلد
    organization = db.Column(db.String(100))  # المنظمة
    
    # Limits
    min_limit = db.Column(db.Float)
    max_limit = db.Column(db.Float)
    target_value = db.Column(db.Float)
    guideline_value = db.Column(db.Float)
    
    # Validity
    effective_date = db.Column(db.Date)  # تاريخ السريان
    expiry_date = db.Column(db.Date)     # تاريخ الانتهاء
    is_active = db.Column(db.Boolean, default=True)
    
    # Additional Information
    notes = db.Column(db.Text)
    reference_document = db.Column(db.String(200))  # المرجع
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parameter = db.relationship('Parameter', backref='standards')
    
    def check_conformity(self, value):
        """فحص المطابقة لهذا المعيار"""
        if value is None:
            return None
        
        conforming = True
        
        if self.min_limit is not None and value < self.min_limit:
            conforming = False
        
        if self.max_limit is not None and value > self.max_limit:
            conforming = False
        
        return {
            'conforming': conforming,
            'value': value,
            'min_limit': self.min_limit,
            'max_limit': self.max_limit,
            'standard': self.standard_name,
            'organization': self.organization
        }
    
    def __repr__(self):
        return f'<ParameterStandard {self.parameter.code} - {self.standard_name}>'