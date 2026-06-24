@echo off
chcp 65001 >nul
cd /d "%~dp0"
title بناء نظام إدارة المعرض - ShowroomERP

echo ============================================================
echo            بناء برنامج إدارة المعرض  (ShowroomERP)
echo ============================================================
echo.

REM ---- 1) التأكد من وجود Python 3.12 ----
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo [خطأ] Python 3.12 غير مثبّت على الجهاز.
  echo.
  echo     ثبّته باحد الطريقتين ثم اعد تشغيل هذا الملف:
  echo       1^) الامر:  py install 3.12
  echo       2^) او نزّله من:  https://www.python.org/downloads/
  echo          ^(اختر Add python to PATH اثناء التثبيت^)
  echo.
  echo     ملاحظة مهمة: لا تستخدم Python 3.14 - غير متوافق مع PyQt6.
  echo.
  pause
  exit /b 1
)
for /f "delims=" %%v in ('py -3.12 --version') do echo [1/3] تم العثور على %%v
echo.

REM ---- 2) تثبيت المكتبات ----
echo [2/3] تثبيت المكتبات المطلوبة... ^(قد ياخذ دقيقة^)
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
py -3.12 -m pip install pyinstaller
if errorlevel 1 (
  echo.
  echo [خطأ] فشل تثبيت المكتبات. تاكد من اتصال الانترنت ثم اعد المحاولة.
  pause
  exit /b 1
)
echo.

REM ---- 3) بناء البرنامج ----
echo [3/3] جاري بناء البرنامج...
py -3.12 -m PyInstaller packaging\showroom_erp.spec --noconfirm
if errorlevel 1 (
  echo.
  echo [خطأ] فشل البناء. انسخ نص الخطأ بالكامل وارسله.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   تم البناء بنجاح
echo   البرنامج جاهز في:
echo   %~dp0dist\ShowroomERP\ShowroomERP.exe
echo.
echo   للتوزيع: انسخ الفولدر كامل  dist\ShowroomERP  على الفلاشة.
echo ============================================================
echo.
explorer "%~dp0dist\ShowroomERP"
pause
