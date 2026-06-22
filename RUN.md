# تشغيل النظام محليًا (من المصدر)

نظام إدارة معرض الدراجات النارية — Python + PyQt6 + SQLite (ويندوز، Offline-First).

## المتطلبات
- Python 3.11+

## الخطوات
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

- أول تشغيل: شاشة **إعداد أوّلي** (اسم المعرض + حساب مدير).
- تسجيل الدخول لاحقًا بحساب المدير الذي أنشأته.

## أين تُخزَّن البيانات؟
```
%LOCALAPPDATA%\ShowroomERP\showroom.db      ← قاعدة البيانات
%LOCALAPPDATA%\ShowroomERP\backups\         ← النسخ الاحتياطية
```
(منفصلة عن ملفات البرنامج، فلا تتأثر بالتحديث.)

## (اختياري) خط Cairo
ضع `Cairo-Regular.ttf` (و`Cairo-Bold.ttf`) في `app/assets/fonts/` ليُستخدم
تلقائيًا؛ بدونه يعمل التطبيق بخط Segoe UI. التفاصيل في `app/assets/fonts/README.md`.

## تبديل القالب
من شاشة **الإعدادات** → القالب (4 قوالب) — يُطبَّق فورًا على كل الشاشات.
