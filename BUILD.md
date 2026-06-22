# بناء تنفيذي ويندوز (PyInstaller)

ملف البناء الرسمي الوحيد: **`packaging/showroom_erp.spec`**.

## المتطلبات (على ويندوز)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

## البناء (من جذر المستودع)
```bat
pyinstaller packaging\showroom_erp.spec
```

## المخرجات
```
dist\ShowroomERP\
├── ShowroomERP.exe                         ← الملف التنفيذي
└── _internal\
    ├── app\theme\themes\                    ← القوالب الأربعة (QSS + JSON)
    ├── app\assets\icons\app.ico             ← الأيقونة
    ├── app\assets\fonts\                     ← خطوط Cairo (إن وُجدت)
    └── (مكتبات Qt/Python المضمّنة)
```

كل الأصول تُحمَّل عبر `app/config.py: resource_path()` المتوافق مع `sys._MEIPASS`،
فلا تنكسر المسارات بعد التغليف. شغّل عبر النقر على `ShowroomERP.exe`.

> ملاحظة: PyInstaller يبني لنظام التشغيل المضيف؛ أنشئ نسخة الويندوز على ويندوز.
> الـ spec نفسه تم التحقق من صحته ببناء كامل وتشغيل النسخة المجمّعة.
