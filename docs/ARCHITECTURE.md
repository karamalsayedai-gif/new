# معمارية النظام — Showroom ERP

## الستاك
Python 3.11+ · PyQt6 (Qt Widgets) · SQLite (`sqlite3`) · QSS Theming · PyInstaller.

## مبدأ الفصل (Clean / Modular)
```
UI (presentation)  →  Services (business logic)  →  Repositories (data access)  →  Database (SQLite)
        │                      │
   ThemeManager          SettingsService
```
- **لا SQL داخل الواجهة.** الواجهة تنادي الخدمات فقط.
- **الخدمات** تحوي كل قواعد العمل (الإقفال، الصلاحيات، النسخ الاحتياطي...).
- **المستودعات** المكان الوحيد الذي يلمس SQLite.
- **الحاوية (`app/core/container.py`)** تُجمّع كل الكائنات وتُمرّرها (DI بسيط).

## الطبقات والمسؤوليات
| الطبقة | المسار | المسؤولية |
|---|---|---|
| التهيئة/الإقلاع | `app/application.py`, `main.py` | إنشاء QApplication، التنقل الجذري |
| الإعداد | `app/config.py` | المسارات (آمنة للتغليف) والثوابت |
| النواة | `app/core/` | الحاوية، الصلاحيات، الأمان، الأدوات |
| النطاق | `app/domain/` | الكيانات (dataclasses) والتعدادات |
| البيانات | `app/data/` | الاتصال، المخطط، الترقيات، البذور، المستودعات |
| الخدمات | `app/services/` | المصادقة، المستخدمون، الإعدادات، الإقفال، النسخ، التدقيق |
| القوالب | `app/theme/` | ThemeManager + محمّل QSS + 4 قوالب منظَّمة |
| الواجهة | `app/ui/` | الشاشات والمكوّنات (أسماء كائنات دلالية) |

## محرك القوالب
- `ThemeManager` (QObject) يطبّق QSS **عالميًا** عبر `QApplication.setStyleSheet`.
- كل قالب = مجلد فيه `manifest.json` (الهوية + تلميحات التخطيط) و`colors.json`
  و`metrics.json` و`typography.json` و`main.qss` (يستخدم رموز `$token`).
- التبديل وقت التشغيل من الإعدادات → `apply()` → إشارة `theme_changed` → إعادة
  بناء التخطيط (موضع/عرض الشريط الجانبي حسب القالب).

## المصادقة و RBAC
`users → roles → role_permissions(code)`. كلمات المرور بـ PBKDF2-HMAC-SHA256.
`AuthService.can(code)` + حراسة العناصر في الواجهة حسب الصلاحية. أدوار جاهزة:
مدير النظام / كاشير / محاسب.

## الإعدادات
جدول `settings(key,value,type)` + `SettingsService` (cache في الذاكرة + getters
مكتوبة). قابل للتوسّع لكل أقسام الإعدادات دون تعديل المخطط.

## النسخ الاحتياطي
`BackupService`: يدوي/تلقائي (حسب فترة)، نسخ آمن عبر `sqlite3.Connection.backup`،
استعادة باستبدال الملف، ونسخ عند الإغلاق. الوجهة في `%LOCALAPPDATA%`.

## الإقفال اليومي
`DayClosingService`: لكل يوم سجل؛ الإقفال يحسب المتوقع، يقارنه بالمعدول، يسجّل
الفرق، ويحوّل الحالة إلى `closed` فتُرفض العمليات الجديدة. إعادة الفتح تتطلب
صلاحية `day.reopen` وتُدوَّن في سجل التدقيق.

## سجل التدقيق
`AuditService.log(...)` يسجّل كل إجراء حسّاس (دخول، إنشاء مستخدم، إقفال/فتح يوم،
نسخ/استعادة) في `audit_log`.

## جاهزية التغليف
مسارات الموارد عبر `resource_path()` المتوافق مع `sys._MEIPASS`. بيانات التشغيل
منفصلة عن الموارد. ملفات `packaging/` جاهزة (spec + Inno Setup).
