"""
نموذج المعايير/المعاملات
"""

from app import db
from datetime import datetime


class Parameter(db.Model):
    """المعايير/المعاملات التحليلية"""
    
    __tablename__ = 'parameters'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(100), nullable=False)
    name_fr = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    unit = db.Column(db.String(20))
    method = db.Column(db.String(100))
    detection_limit = db.Column(db.Numeric(15, 6))
    precision = db.Column(db.Numeric(5, 2))
    
    # القيم المعيارية
    norm_min = db.Column(db.Numeric(15, 6))
    norm_max = db.Column(db.Numeric(15, 6))
    norm_ideal = db.Column(db.Numeric(15, 6))
    norm_reference = db.Column(db.String(100))
    
    # صيغة الحساب
    calculation_formula = db.Column(db.Text)
    
    # التحاليل التي يظهر فيها
    in_partial = db.Column(db.Boolean, default=False)
    in_complete = db.Column(db.Boolean, default=True)
    in_bacteriological = db.Column(db.Boolean, default=False)
    
    display_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    results = db.relationship('Result', backref='parameter', lazy='dynamic')
    
    @property
    def category_ar(self):
        """الفئة بالعربية"""
        categories = {
            'organoleptic': 'أورغانوليبتيكية',
            'physicochemical': 'فيزيوكيميائية',
            'mineralization': 'معادن',
            'pollution': 'تلوث',
            'bacteriological': 'بكتريولوجية',
            'undesirable': 'غير مرغوبة',
            'ionic': 'أيونية'
        }
        return categories.get(self.category, self.category)
    
    @property
    def norm_range(self):
        """المدى المعياري كنص"""
        if self.norm_min and self.norm_max:
            return f"{self.norm_min} - {self.norm_max}"
        elif self.norm_max:
            return f"≤ {self.norm_max}"
        elif self.norm_min:
            return f"≥ {self.norm_min}"
        return "غير محدد"
    
    def check_compliance(self, value):
        """فحص مطابقة قيمة معينة"""
        if value is None:
            return None
        
        value = float(value)
        
        # التحقق من تجاوز الحدود
        if self.norm_max is not None and value > float(self.norm_max):
            return 'non_compliant'
        
        if self.norm_min is not None and value < float(self.norm_min):
            return 'non_compliant'
        
        # التحقق من القرب من الحد (90% من الحد الأقصى)
        if self.norm_max is not None:
            threshold = float(self.norm_max) * 0.9
            if value >= threshold:
                return 'warning'
        
        return 'compliant'
    
    def calculate_value(self, base_value, **kwargs):
        """حساب القيمة باستخدام الصيغة (إن وجدت)"""
        if not self.calculation_formula:
            return base_value
        
        try:
            # استبدال المتغيرات في الصيغة
            formula = self.calculation_formula
            formula = formula.replace('value', str(base_value))
            
            for key, val in kwargs.items():
                formula = formula.replace(f'[{key}]', str(val))
            
            # تقييم الصيغة (يمكن استخدام مكتبة أكثر أماناً)
            result = eval(formula)
            return round(result, 6)
        except:
            return base_value
    
    def __repr__(self):
        return f'<Parameter {self.code}>'