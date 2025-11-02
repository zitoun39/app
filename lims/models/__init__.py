# LIMS Models - نماذج قاعدة البيانات
# Database Models for Water Quality LIMS

# Initialize db instance
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# Import all models and enums
from .user import User, UserRole
from .sample import Sample, SampleType, SampleStatus
from .parameter import Parameter, ParameterCategory
from .result import Result, TestResult, ResultStatus, QualityFlag
from .equipment import Equipment, Calibration

# Make db available
__all__ = [
    'db',
    'User', 'UserRole',
    'Sample', 'SampleType',
    'Parameter', 'ParameterCategory',
    'Result', 'TestResult',
    'Equipment', 'Calibration'
]