# -*- mode: python ; coding: utf-8 -*-
"""ملف مواصفات PyInstaller لبناء تطبيق ويندوز (مجلد تشغيل onedir).

يُشغَّل من جذر المستودع:
    pyinstaller packaging/showroom_erp.spec

المسارات تُحسب نسبةً إلى جذر المستودع (مجلد الـ spec الأب) لتعمل أينما شُغِّل
الأمر. يُضمّن كل الأصول غير البرمجية (القوالب + الأيقونات + خطوط Cairo) لتُحمَّل
عبر مسارات آمنة للتغليف (app/config.py: resource_path الذي يتعامل مع sys._MEIPASS).
بيانات التشغيل (قاعدة البيانات/النسخ) تُكتب في %LOCALAPPDATA% خارج الحزمة.
"""
import os

# SPECPATH يُحقن من PyInstaller = مجلد ملف الـ spec (packaging/). الجذر هو الأب.
ROOT = os.path.dirname(SPECPATH)

block_cipher = None

# الأصول الثابتة المضمّنة: (المصدر على القرص، الوجهة داخل الحزمة)
datas = [
    (os.path.join(ROOT, 'app/theme/themes'), 'app/theme/themes'),
    (os.path.join(ROOT, 'app/assets/icons'), 'app/assets/icons'),
    (os.path.join(ROOT, 'app/assets/fonts'), 'app/assets/fonts'),
]

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ShowroomERP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                 # تطبيق نافذي بلا نافذة طرفية
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'app/assets/icons/app.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ShowroomERP',
)
