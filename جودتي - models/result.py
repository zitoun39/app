"""
نموذج النتائج
"""

from app import db
from datetime import datetime
from sqlalchemy import event


class Result(db.Model):
    """نتائج التحاليل"""
    
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), nullable=False, index=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False, index=True)
    
    # القيمة المقاسة
    measured_value = db.Column(db.Numeric(15, 6))
    unit = db.Column(db.String(20))
    
    # تفاصيل التحليل
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    method_used = db.Column(db.String(100))
    equipment_used = db.Column(db.String(100))
    
    # المطابقة
    compliance = db.Column(db.String(20))  # compliant, warning, non_compliant
    exceeds_limit = db.Column(db.Boolean, default=False)
    
    # المحلل
    analyst_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # الملاحظات
    remarks = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('sample_id', 'parameter_id', name='uq_sample_parameter'),
    )
    
    @property
    def compliance_badge(self):
        """شارة المطابقة مع اللون"""
        if not self.compliance:
            return '<span class="badge bg-secondary">-</span>'
        
        badges = {
            'compliant': '<span class="badge bg-success">✓ مطابق</span>',
            'warning': '<span class="badge bg-warning text-dark">⚠ قريب</span>',
            'non_compliant': '<span class="badge bg-danger">✗ غير مطابق</span>'
        }
        return badges.get(self.compliance, '')
    
    @property
    def value_formatted(self):
        """القيمة منسقة"""
        if self.measured_value is None:
            return '-'
        
        # تنسيق حسب الدقة
        if self.measured_value == int(self.measured_value):
            return str(int(self.measured_value))
        else:
            return f"{float(self.measured_value):.2f}"
    
    def check_and_update_compliance(self):
        """فحص وتحديث حالة المطابقة"""
        if self.measured_value is None or not self.parameter:
            return
        
        self.compliance = self.parameter.check_compliance(self.measured_value)
        
        # التحقق من تجاوز الحد
        if self.parameter.norm_max:
            self.exceeds_limit = float(self.measured_value) > float(self.parameter.norm_max)
        elif self.parameter.norm_min:
            self.exceeds_limit = float(self.measured_value) < float(self.parameter.norm_min)
        else:
            self.exceeds_limit = False
    
    def __repr__(self):
        return f'<Result S{self.sample_id}-P{self.parameter_id}>'


# Event Listener: تحديث المطابقة تلقائياً عند تغيير القيمة
@event.listens_for(Result.measured_value, 'set')
def update_compliance_on_value_change(target, value, oldvalue, initiator):
    """تحديث المطابقة تلقائياً عند تغيير القيمة"""
    if value is not None and target.parameter:
        target.check_and_update_compliance()