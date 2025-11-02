-- ═══════════════════════════════════════════════════════════
-- جودتي - نظام إدارة مخبر مراقبة جودة المياه
-- سكريبت إنشاء قاعدة البيانات
-- ═══════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════
-- 1. جدول المستخدمين
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) NOT NULL, -- admin, supervisor, analyst, validator, viewer
    phone VARCHAR(20),
    signature TEXT, -- التوقيع الرقمي (base64)
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- ═══════════════════════════════════════════════════════════
-- 2. جدول أنواع العينات
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sample_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) UNIQUE NOT NULL, -- Tr, Rw, Ds, etc.
    name_ar VARCHAR(100) NOT NULL,
    name_fr VARCHAR(100) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════
-- 3. جدول المعايير/المعاملات
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL, -- pH, Turb, Cl, etc.
    name_ar VARCHAR(100) NOT NULL,
    name_fr VARCHAR(100) NOT NULL,
    category VARCHAR(30) NOT NULL, -- physicochemical, bacteriological, etc.
    unit VARCHAR(20), -- mg/L, NTU, UFC/100mL, etc.
    method VARCHAR(100), -- ISO 7027, NF EN 27888, etc.
    detection_limit DECIMAL(15, 6),
    precision DECIMAL(5, 2),
    
    -- القيم المعيارية (المرسوم 11-219)
    norm_min DECIMAL(15, 6),
    norm_max DECIMAL(15, 6),
    norm_ideal DECIMAL(15, 6),
    norm_reference VARCHAR(100), -- المرجع القانوني
    
    -- صيغة الحساب (اختياري)
    calculation_formula TEXT,
    
    -- التحاليل التي يظهر فيها
    in_partial BOOLEAN DEFAULT 0,
    in_complete BOOLEAN DEFAULT 1,
    in_bacteriological BOOLEAN DEFAULT 0,
    
    display_order INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════
-- 4. جدول العينات
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL, -- Tr25-0001
    
    -- معلومات الأخذ
    collection_date DATE NOT NULL,
    reception_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    sample_type_id INTEGER NOT NULL,
    
    -- الموقع
    location_name VARCHAR(200) NOT NULL, -- نقطة الأخذ
    commune VARCHAR(100),
    wilaya VARCHAR(100) DEFAULT 'سطيف',
    
    -- الشخص الذي جمع العينة
    collector_id INTEGER NOT NULL,
    
    -- معلومات إضافية
    temperature DECIMAL(4, 2), -- درجة الحرارة عند الأخذ
    weather_conditions TEXT,
    transport_conditions TEXT,
    
    -- نوع التحليل المطلوب
    analysis_type VARCHAR(30) NOT NULL, -- partial, complete, bacteriological, custom
    
    -- الحالة
    status VARCHAR(20) DEFAULT 'pending', -- pending, in_progress, completed, archived
    
    -- المحلل والمراجع
    analyst_id INTEGER,
    validator_id INTEGER,
    analysis_date DATE,
    validation_date DATE,
    
    -- الملاحظات
    notes TEXT,
    observations TEXT,
    
    -- المطابقة
    compliance_status VARCHAR(20), -- compliant, non_compliant, warning
    
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sample_type_id) REFERENCES sample_types(id),
    FOREIGN KEY (collector_id) REFERENCES users(id),
    FOREIGN KEY (analyst_id) REFERENCES users(id),
    FOREIGN KEY (validator_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- ═══════════════════════════════════════════════════════════
-- 5. جدول النتائج
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER NOT NULL,
    parameter_id INTEGER NOT NULL,
    
    -- القيمة المقاسة
    measured_value DECIMAL(15, 6),
    unit VARCHAR(20),
    
    -- تفاصيل التحليل
    analysis_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    method_used VARCHAR(100),
    equipment_used VARCHAR(100),
    
    -- المطابقة
    compliance VARCHAR(20), -- compliant, warning, non_compliant
    exceeds_limit BOOLEAN DEFAULT 0,
    
    -- المحلل
    analyst_id INTEGER,
    
    -- الملاحظات
    remarks TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sample_id) REFERENCES samples(id) ON DELETE CASCADE,
    FOREIGN KEY (parameter_id) REFERENCES parameters(id),
    FOREIGN KEY (analyst_id) REFERENCES users(id),
    
    UNIQUE(sample_id, parameter_id)
);

-- ═══════════════════════════════════════════════════════════
-- 6. جدول المعدات
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    acquisition_date DATE,
    
    -- المعايرة
    last_calibration_date DATE,
    next_calibration_date DATE,
    calibration_certificate VARCHAR(255), -- مسار الشهادة
    
    -- الحالة
    status VARCHAR(20) DEFAULT 'operational', -- operational, maintenance, out_of_service
    
    notes TEXT,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════
-- 7. جدول سجل المعايرات
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS calibrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    calibration_date DATE NOT NULL,
    next_due_date DATE NOT NULL,
    performed_by VARCHAR(100),
    organization VARCHAR(200),
    certificate_number VARCHAR(100),
    certificate_path VARCHAR(255),
    result VARCHAR(20), -- compliant, non_compliant, adjusted
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (equipment_id) REFERENCES equipment(id)
);

-- ═══════════════════════════════════════════════════════════
-- 8. جدول سجل النشاطات (Audit Trail)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL, -- create, update, delete, login, etc.
    entity_type VARCHAR(50), -- sample, result, parameter, etc.
    entity_id INTEGER,
    description TEXT,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ═══════════════════════════════════════════════════════════
-- 9. جدول تسلسل الأكواد
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS code_sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_type_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    last_sequence INTEGER DEFAULT 0,
    
    FOREIGN KEY (sample_type_id) REFERENCES sample_types(id),
    UNIQUE(sample_type_id, year)
);

-- ═══════════════════════════════════════════════════════════
-- 10. جدول النسخ الاحتياطية
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    backup_type VARCHAR(20), -- auto, manual
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- ═══════════════════════════════════════════════════════════
-- الفهارس لتحسين الأداء
-- ═══════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_samples_code ON samples(code);
CREATE INDEX IF NOT EXISTS idx_samples_date ON samples(collection_date);
CREATE INDEX IF NOT EXISTS idx_samples_status ON samples(status);
CREATE INDEX IF NOT EXISTS idx_samples_type ON samples(sample_type_id);
CREATE INDEX IF NOT EXISTS idx_results_sample ON results(sample_id);
CREATE INDEX IF NOT EXISTS idx_results_parameter ON results(parameter_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_date ON activity_logs(created_at);