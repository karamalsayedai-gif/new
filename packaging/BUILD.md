# بناء وتشغيل التطبيق على ويندوز (بعد التغليف)

## 1) تجهيز البيئة
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

## 2) (اختياري) إضافة خط Cairo
نزّل خط Cairo من https://fonts.google.com/specimen/Cairo وضع:
```
app\assets\fonts\Cairo-Regular.ttf
app\assets\fonts\Cairo-Bold.ttf
```
بدونه يعمل التطبيق بخط Segoe UI تلقائيًا.

## 3) البناء (من جذر المستودع)
```bat
pyinstaller packaging\showroom_erp.spec
```
الناتج: مجلد تشغيل كامل في `dist\ShowroomERP\` فيه `ShowroomERP.exe`.

ما يُضمَّن تلقائيًا داخل الحزمة (عبر `datas` في الـ spec):
- `app/theme/themes` — القوالب الأربعة (QSS + JSON).
- `app/assets/icons/app.ico` — أيقونة التطبيق.
- `app/assets/fonts` — خطوط Cairo إن وُجدت.

كل هذه الملفات تُقرأ عبر `resource_path()` المتوافق مع `sys._MEIPASS`، فلا تنكسر
المسارات بعد التغليف.

## 4) التشغيل
شغّل `dist\ShowroomERP\ShowroomERP.exe`. أول تشغيل يطلب إعدادًا أوّليًا
(اسم المعرض + حساب مدير). بيانات التشغيل والنسخ الاحتياطية تُخزَّن في:
```
%LOCALAPPDATA%\ShowroomERP\
```

## 5) (اختياري) مُثبّت بنقرة واحدة
ثبّت [Inno Setup](https://jrsoftware.org/isinfo.php) ثم افتح
`packaging\installer.iss` واضغط Build لإخراج `ShowroomERP_Setup_x.x.x.exe`.
