import os
import shutil
import hashlib
import mimetypes
from datetime import datetime
from typing import Optional, Tuple, BinaryIO
from pathlib import Path
import logging

# إعداد المسجل
logger = logging.getLogger(__name__)

class FileStorage:
    """مدير تخزين الملفات"""
    
    def __init__(self, base_path: str = "data/documents"):
        """تهيئة مدير التخزين
        
        Args:
            base_path: المسار الأساسي لتخزين الملفات
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # إنشاء المجلدات الفرعية
        self.create_directory_structure()
    
    def create_directory_structure(self):
        """إنشاء هيكل المجلدات"""
        directories = [
            'documents',  # المستندات الأصلية
            'thumbnails', # الصور المصغرة
            'versions',   # إصدارات المستندات
            'temp',       # الملفات المؤقتة
            'backup'      # النسخ الاحتياطية
        ]
        
        for directory in directories:
            dir_path = self.base_path / directory
            dir_path.mkdir(exist_ok=True)
            logger.debug(f"تم إنشاء المجلد: {dir_path}")
    
    def generate_file_hash(self, file_path: str) -> str:
        """توليد hash للملف
        
        Args:
            file_path: مسار الملف
            
        Returns:
            SHA-256 hash للملف
        """
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"خطأ في توليد hash للملف {file_path}: {str(e)}")
            return ""
    
    def get_file_info(self, file_path: str) -> dict:
        """الحصول على معلومات الملف
        
        Args:
            file_path: مسار الملف
            
        Returns:
            معلومات الملف
        """
        try:
            file_stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1]
            mime_type, _ = mimetypes.guess_type(file_path)
            
            return {
                'name': file_name,
                'size': file_stat.st_size,
                'extension': file_ext,
                'mime_type': mime_type or 'application/octet-stream',
                'created_at': datetime.fromtimestamp(file_stat.st_ctime),
                'modified_at': datetime.fromtimestamp(file_stat.st_mtime),
                'hash': self.generate_file_hash(file_path)
            }
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات الملف {file_path}: {str(e)}")
            return {}
    
    def generate_storage_path(self, original_filename: str, document_id: Optional[int] = None) -> str:
        """توليد مسار التخزين
        
        Args:
            original_filename: اسم الملف الأصلي
            document_id: معرف المستند (اختياري)
            
        Returns:
            مسار التخزين النسبي
        """
        # استخدام التاريخ الحالي لتنظيم الملفات
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        
        # إنشاء اسم ملف فريد
        timestamp = now.strftime('%H%M%S')
        file_ext = os.path.splitext(original_filename)[1]
        
        if document_id:
            filename = f"doc_{document_id}_{timestamp}{file_ext}"
        else:
            filename = f"{timestamp}_{original_filename}"
        
        # مسار التخزين
        storage_path = os.path.join('documents', year, month, day, filename)
        
        return storage_path
    
    def store_file(self, source_path: str, original_filename: str, document_id: Optional[int] = None) -> Tuple[str, dict]:
        """تخزين ملف
        
        Args:
            source_path: مسار الملف المصدر
            original_filename: اسم الملف الأصلي
            document_id: معرف المستند
            
        Returns:
            tuple: (مسار التخزين, معلومات الملف)
        """
        try:
            # توليد مسار التخزين
            storage_path = self.generate_storage_path(original_filename, document_id)
            full_storage_path = self.base_path / storage_path
            
            # إنشاء المجلدات إذا لم تكن موجودة
            full_storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # نسخ الملف
            shutil.copy2(source_path, full_storage_path)
            
            # الحصول على معلومات الملف
            file_info = self.get_file_info(str(full_storage_path))
            
            logger.info(f"تم تخزين الملف: {storage_path}")
            return storage_path, file_info
            
        except Exception as e:
            logger.error(f"خطأ في تخزين الملف {source_path}: {str(e)}")
            raise
    
    def store_uploaded_file(self, uploaded_file: BinaryIO, original_filename: str, document_id: Optional[int] = None) -> Tuple[str, dict]:
        """تخزين ملف مرفوع
        
        Args:
            uploaded_file: الملف المرفوع
            original_filename: اسم الملف الأصلي
            document_id: معرف المستند
            
        Returns:
            tuple: (مسار التخزين, معلومات الملف)
        """
        try:
            # توليد مسار التخزين
            storage_path = self.generate_storage_path(original_filename, document_id)
            full_storage_path = self.base_path / storage_path
            
            # إنشاء المجلدات إذا لم تكن موجودة
            full_storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # حفظ الملف
            with open(full_storage_path, 'wb') as f:
                shutil.copyfileobj(uploaded_file, f)
            
            # الحصول على معلومات الملف
            file_info = self.get_file_info(str(full_storage_path))
            
            logger.info(f"تم تخزين الملف المرفوع: {storage_path}")
            return storage_path, file_info
            
        except Exception as e:
            logger.error(f"خطأ في تخزين الملف المرفوع {original_filename}: {str(e)}")
            raise
    
    def get_full_path(self, storage_path: str) -> str:
        """الحصول على المسار الكامل للملف
        
        Args:
            storage_path: مسار التخزين النسبي
            
        Returns:
            المسار الكامل
        """
        return str(self.base_path / storage_path)
    
    def file_exists(self, storage_path: str) -> bool:
        """التحقق من وجود الملف
        
        Args:
            storage_path: مسار التخزين النسبي
            
        Returns:
            True إذا كان الملف موجود
        """
        full_path = self.get_full_path(storage_path)
        return os.path.exists(full_path)
    
    def delete_file(self, storage_path: str) -> bool:
        """حذف ملف
        
        Args:
            storage_path: مسار التخزين النسبي
            
        Returns:
            True إذا تم الحذف بنجاح
        """
        try:
            full_path = self.get_full_path(storage_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"تم حذف الملف: {storage_path}")
                return True
            else:
                logger.warning(f"الملف غير موجود: {storage_path}")
                return False
        except Exception as e:
            logger.error(f"خطأ في حذف الملف {storage_path}: {str(e)}")
            return False
    
    def create_version(self, original_storage_path: str, version_number: str) -> str:
        """إنشاء إصدار من الملف
        
        Args:
            original_storage_path: مسار الملف الأصلي
            version_number: رقم الإصدار
            
        Returns:
            مسار إصدار الملف
        """
        try:
            original_full_path = self.get_full_path(original_storage_path)
            
            if not os.path.exists(original_full_path):
                raise FileNotFoundError(f"الملف الأصلي غير موجود: {original_storage_path}")
            
            # توليد مسار الإصدار
            original_filename = os.path.basename(original_storage_path)
            name, ext = os.path.splitext(original_filename)
            version_filename = f"{name}_v{version_number}{ext}"
            
            version_storage_path = os.path.join('versions', version_filename)
            version_full_path = self.base_path / version_storage_path
            
            # إنشاء مجلد الإصدارات إذا لم يكن موجود
            version_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # نسخ الملف
            shutil.copy2(original_full_path, version_full_path)
            
            logger.info(f"تم إنشاء إصدار: {version_storage_path}")
            return version_storage_path
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء إصدار للملف {original_storage_path}: {str(e)}")
            raise
    
    def get_storage_stats(self) -> dict:
        """الحصول على إحصائيات التخزين
        
        Returns:
            إحصائيات التخزين
        """
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except OSError:
                        continue
            
            return {
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'base_path': str(self.base_path)
            }
        except Exception as e:
            logger.error(f"خطأ في الحصول على إحصائيات التخزين: {str(e)}")
            return {}

# إنشاء مثيل عام
file_storage = FileStorage()