# التغليف والتوزيع على ويندوز

## المتطلبات (على جهاز ويندوز للبناء)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

## 1) بناء التنفيذي بـ PyInstaller
يُشغَّل من **جذر المستودع**:
```bat
pyinstaller packaging\showroom_erp.spec
```
- الناتج في `dist\ShowroomERP\`.
- قوالب الثيم والأصول تُضمَّن تلقائيًا (انظر `datas` في ملف الـ spec).
- المسارات آمنة للتغليف عبر `app/config.py: resource_path()` الذي يتعامل مع
  `sys._MEIPASS`.
- بيانات التشغيل (قاعدة البيانات والنسخ الاحتياطية) تُكتب في
  `%LOCALAPPDATA%\ShowroomERP` خارج مجلد التثبيت — آمن للتحديثات.

> لإضافة أيقونة: ضع `app\assets\icons\app.ico` قبل البناء.

## 2) إنشاء مُثبّت (Inno Setup)
1. ثبّت [Inno Setup](https://jrsoftware.org/isinfo.php).
2. افتح `packaging\installer.iss`.
3. اضغط **Build** للحصول على `ShowroomERP_Setup_1.0.0.exe`.

## ملاحظات قابلية البيع
- كل معرض يحصل على نسخة قائمة بذاتها؛ بياناته معزولة في `%LOCALAPPDATA%`.
- التخصيص (اسم المعرض/الشعار/القالب) من داخل الإعدادات بلا إعادة بناء.
- ترقية الإصدارات تعتمد نظام Migrations في `app/data/migrations.py` دون فقد بيانات.
