# نظام إدارة معرض الدراجات النارية — Showroom ERP

تطبيق **سطح مكتب (Windows)** يعمل دون اتصال (Offline-First) لإدارة معارض الدراجات
النارية في مصر. واجهة **عربية RTL** بالكامل، قاعدة بيانات **SQLite** محلية، و**محرك
قوالب (4 قوالب)** قابل للتبديل من الإعدادات. معمارية **modular** قابلة للبيع لمعارض أخرى.

## الستاك التقني
- **Python 3.11+**
- **PyQt6** (Qt Widgets) — واجهة احترافية + RTL + تنسيق QSS قوي.
- **SQLite** (`sqlite3` المضمّنة) — بلا خادم، ملف محلي واحد.
- **PBKDF2-HMAC-SHA256** (مكتبة `hashlib`) لتجزئة كلمات المرور.
- **PyInstaller + Inno Setup** للتغليف والتثبيت على ويندوز.

## الفصل المعماري
```
app/ui          ← الواجهات والمكوّنات (لا SQL هنا إطلاقًا)
app/services    ← منطق العمل (المصادقة، الإقفال، النسخ الاحتياطي...)
app/data        ← قاعدة البيانات + المستودعات (المكان الوحيد للـ SQL)
app/domain      ← الكيانات (dataclasses) والتعدادات
app/theme       ← محرك القوالب (QSS + theme.json) + 4 قوالب
app/core        ← أدوات مشتركة (تجزئة، تنسيق، صلاحيات، إعدادات)
```

## التشغيل
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
أول تشغيل ينشئ قاعدة البيانات تلقائيًا ويطلب **إعدادًا أوّليًا** (اسم المعرض + حساب مدير).

## التغليف (ويندوز)
يُبنى عبر ملف الـ spec الجاهز من جذر المستودع:
```bat
pyinstaller packaging\showroom_erp.spec
```
ثم توليد مُثبّت عبر Inno Setup من `packaging\installer.iss`.
التفاصيل الكاملة في `packaging/README.md`.

## القوالب
4 قوالب جاهزة في `app/theme/themes/`: `classic_business`, `modern_dark`,
`compact_admin`, `elegant_light`. كل قالب مجلد يحتوي:
`manifest.json` · `colors.json` · `metrics.json` · `typography.json` · `main.qss`.
لإضافة قالب جديد: انسخ مجلدًا وعدّل ملفاته — يُكتشف تلقائيًا ويظهر في الإعدادات.
التبديل من **الإعدادات** ويُطبَّق فورًا على كل الشاشات عبر `QApplication.setStyleSheet`.

## الأرشيف
المشروع السابق (تطبيق Flutter "حساباتي") محفوظ في `legacy/` ولا علاقة له بهذا المشروع.
