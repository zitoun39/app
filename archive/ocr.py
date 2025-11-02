import os
import logging
from typing import Optional, Tuple
from PIL import Image
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path
import tempfile

# إعداد المسجل
logger = logging.getLogger(__name__)

class OCRProcessor:
    """معالج OCR للمستندات"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """تهيئة معالج OCR
        
        Args:
            tesseract_path: مسار Tesseract إذا لم يكن في PATH
        """
        self.tesseract_available = False
        
        # محاولة تحديد مسار Tesseract
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            # مسارات Tesseract الشائعة على Windows
            common_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
            ]
            
            for path in common_paths:
                expanded_path = os.path.expandvars(path)
                if os.path.exists(expanded_path):
                    pytesseract.pytesseract.tesseract_cmd = expanded_path
                    break
        
        # التحقق من توفر Tesseract
        try:
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("تم العثور على Tesseract OCR بنجاح")
        except Exception as e:
            logger.warning(f"Tesseract OCR غير متوفر: {str(e)}")
            logger.info("لتفعيل OCR، يرجى تثبيت Tesseract من: https://github.com/UB-Mannheim/tesseract/wiki")
        
        # اللغات المدعومة
        self.supported_languages = {
            'ara': 'Arabic',
            'eng': 'English',
            'ara+eng': 'Arabic + English'
        }
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """معالجة مسبقة للصورة لتحسين OCR
        
        Args:
            image_path: مسار الصورة
            
        Returns:
            الصورة المعالجة
        """
        try:
            # قراءة الصورة
            img = cv2.imread(image_path)
            
            # تحويل إلى رمادي
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # تطبيق فلتر لإزالة الضوضاء
            denoised = cv2.medianBlur(gray, 5)
            
            # تحسين التباين
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # تطبيق threshold للحصول على صورة ثنائية
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return binary
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الصورة {image_path}: {str(e)}")
            # إرجاع الصورة الأصلية في حالة الخطأ
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    def extract_text_from_image(self, image_path: str, language: str = 'ara') -> Tuple[str, int]:
        """استخراج النص من الصورة
        
        Args:
            image_path: مسار الصورة
            language: لغة OCR
            
        Returns:
            tuple: (النص المستخرج, مستوى الثقة)
        """
        if not self.tesseract_available:
            logger.warning("OCR غير متوفر - Tesseract غير مثبت")
            return "OCR غير متوفر - يرجى تثبيت Tesseract OCR", 0
            
        try:
            # معالجة مسبقة للصورة
            processed_img = self.preprocess_image(image_path)
            
            # تحويل إلى PIL Image
            pil_img = Image.fromarray(processed_img)
            
            # استخراج النص مع معلومات الثقة
            data = pytesseract.image_to_data(pil_img, lang=language, output_type=pytesseract.Output.DICT)
            
            # حساب متوسط الثقة
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) // len(confidences) if confidences else 0
            
            # استخراج النص
            text = pytesseract.image_to_string(pil_img, lang=language)
            
            # تنظيف النص
            cleaned_text = self.clean_text(text)
            
            logger.info(f"تم استخراج النص من {image_path} بثقة {avg_confidence}%")
            return cleaned_text, avg_confidence
            
        except Exception as e:
            logger.error(f"خطأ في استخراج النص من {image_path}: {str(e)}")
            return "", 0
    
    def extract_text_from_pdf(self, pdf_path: str, language: str = 'ara') -> Tuple[str, int]:
        """استخراج النص من ملف PDF
        
        Args:
            pdf_path: مسار ملف PDF
            language: لغة OCR
            
        Returns:
            tuple: (النص المستخرج, مستوى الثقة)
        """
        if not self.tesseract_available:
            logger.warning("OCR غير متوفر - Tesseract غير مثبت")
            return "OCR غير متوفر - يرجى تثبيت Tesseract OCR", 0
            
        try:
            # تحويل PDF إلى صور
            pages = convert_from_path(pdf_path, dpi=300)
            
            all_text = []
            all_confidences = []
            
            # معالجة كل صفحة
            for i, page in enumerate(pages):
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    # حفظ الصفحة كصورة مؤقتة
                    page.save(temp_file.name, 'PNG')
                    
                    # استخراج النص من الصورة
                    text, confidence = self.extract_text_from_image(temp_file.name, language)
                    
                    if text.strip():
                        all_text.append(f"--- الصفحة {i+1} ---\n{text}")
                        all_confidences.append(confidence)
                    
                    # حذف الملف المؤقت
                    os.unlink(temp_file.name)
            
            # دمج النصوص
            combined_text = "\n\n".join(all_text)
            avg_confidence = sum(all_confidences) // len(all_confidences) if all_confidences else 0
            
            logger.info(f"تم استخراج النص من {pdf_path} ({len(pages)} صفحة) بثقة {avg_confidence}%")
            return combined_text, avg_confidence
            
        except Exception as e:
            logger.error(f"خطأ في استخراج النص من PDF {pdf_path}: {str(e)}")
            return "", 0
    
    def clean_text(self, text: str) -> str:
        """تنظيف النص المستخرج
        
        Args:
            text: النص الخام
            
        Returns:
            النص المنظف
        """
        if not text:
            return ""
        
        # إزالة الأسطر الفارغة الزائدة
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        
        # دمج الأسطر
        cleaned = '\n'.join(lines)
        
        # إزالة المسافات الزائدة
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def process_document(self, file_path: str, language: str = 'ara') -> Tuple[str, int]:
        """معالجة مستند واستخراج النص
        
        Args:
            file_path: مسار الملف
            language: لغة OCR
            
        Returns:
            tuple: (النص المستخرج, مستوى الثقة)
        """
        if not os.path.exists(file_path):
            logger.error(f"الملف غير موجود: {file_path}")
            return "", 0
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path, language)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return self.extract_text_from_image(file_path, language)
        else:
            logger.warning(f"نوع الملف غير مدعوم: {file_ext}")
            return "", 0
    
    def get_supported_languages(self) -> dict:
        """الحصول على اللغات المدعومة
        
        Returns:
            قاموس اللغات المدعومة
        """
        return self.supported_languages
    
    def is_language_supported(self, language: str) -> bool:
        """التحقق من دعم اللغة
        
        Args:
            language: كود اللغة
            
        Returns:
            True إذا كانت اللغة مدعومة
        """
        return language in self.supported_languages
    
    def is_available(self) -> bool:
        """التحقق من توفر OCR
        
        Returns:
            True إذا كان OCR متوفراً
        """
        return self.tesseract_available
    
    def get_status(self) -> dict:
        """الحصول على حالة OCR
        
        Returns:
            معلومات حالة OCR
        """
        status = {
            'available': self.tesseract_available,
            'supported_languages': self.supported_languages
        }
        
        if self.tesseract_available:
            try:
                status['version'] = pytesseract.get_tesseract_version()
            except:
                status['version'] = 'غير معروف'
        else:
            status['message'] = 'يرجى تثبيت Tesseract OCR من: https://github.com/UB-Mannheim/tesseract/wiki'
            
        return status

# إنشاء مثيل عام
ocr_processor = OCRProcessor()

def process_document_ocr(file_path: str, language: str = 'ara') -> Tuple[str, int]:
    """دالة مساعدة لمعالجة المستندات
    
    Args:
        file_path: مسار الملف
        language: لغة OCR
        
    Returns:
        tuple: (النص المستخرج, مستوى الثقة)
    """
    return ocr_processor.process_document(file_path, language)