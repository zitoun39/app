# جودتي (Jawdati) LIMS & Archive

نظام جودتي يجمع بين إدارة معلومات المختبر (LIMS) ووحدة أرشيف إلكتروني مزودة بـ OCR وفهرسة نصية. يعتمد المشروع على Flask وSQLite ويستهدف التشغيل في بيئة داخلية مع ضوابط أمان مشددة.

## المحتويات
- [التهيئة السريعة](#التهيئة-السريعة)
- [الإعداد البيئي](#الإعداد-البيئي)
- [التشغيل](#التشغيل)
- [الاختبارات وضمان الجودة](#الاختبارات-وضمان-الجودة)
- [النسخ الاحتياطي والتشفير](#النسخ-الاحتياطي-والتشفير)
- [مخطط قاعدة البيانات](#مخطط-قاعدة-البيانات)
- [التطوير المستقبلي](#التطوير-المستقبلي)

## التهيئة السريعة
1. انسخ ملف المتغيرات البيئية ثم عدِّل القيم حسب بيئتك:
   ```bash
   cp .env.example .env
   ```
2. ثبّت المتطلبات:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

## الإعداد البيئي
- يجب توفير متغير `SECRET_KEY` قبل تشغيل التطبيق.
- `DATABASE_URI` يُشير افتراضيًا إلى `sqlite:///data/jawdati.db` ويتم إنشاء المجلد تلقائيًا.
- اضبط `SESSION_COOKIE_SECURE` على `true` في بيئات HTTPS.
- عرّف `TESSERACT_CMD` إذا لم يكن الأمر `tesseract` متاحًا على الـ PATH.
- لتفعيل رفع النسخ الاحتياطية إلى Google Drive أضف بيانات الخدمة في `GOOGLE_DRIVE_CREDENTIALS_FILE`.

## التشغيل
```bash
export FLASK_APP=app:create_app
flask --app app run --debug
```
يُنشئ التطبيق الجداول تلقائيًا عند أول تشغيل في حال عدم استخدام Alembic. يُنصح باستخدام Alembic للترحيلات في البيئات الإنتاجية.

## الاختبارات وضمان الجودة
- اختبارات الوحدة والتناغم:
  ```bash
  pytest
  ```
- يتم تشغيل `flake8`, `pytest`, `bandit`, و`safety` تلقائيًا عبر GitHub Actions (راجع `.github/workflows/ci.yml`).

## النسخ الاحتياطي والتشفير
- وحدة `backups/encrypt.py` توفر دوال `encrypt_file` و`decrypt_file` باستخدام `cryptography.Fernet` لضمان سرية النسخ الاحتياطية قبل رفعها إلى Google Drive أو أي وسيط آخر.
- استخدم `load_key` أو `generate_key_file` لتخزين مفتاح التشفير في مسار آمن خارج المستودع.

## مخطط قاعدة البيانات
تُدار جميع النماذج عبر `extensions.db` بما في ذلك الأرشيف. الجداول الرئيسية:
- `users`, `user_sessions`
- `samples`, `sample_types`, `results`, `parameters`
- `documents`, `document_versions`, `search_index`, `categories`

## التطوير المستقبلي
- دمج طابور مهام (Celery أو RQ) لمعالجة OCR وتوليد التقارير خارج طلبات HTTP.
- إعداد ترحيلات Alembic رسمية وإضافة دعم PostgreSQL.
- تحسين مولد التقارير للاستفادة من قوالب HTML/PDF مخزّنة مؤقتًا.
