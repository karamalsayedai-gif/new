@echo off
chcp 65001 >nul
cd /d "%~dp0"
title تشغيل نظام إدارة المعرض - ShowroomERP

REM التاكد من Python 3.12
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo [خطأ] Python 3.12 غير مثبّت. ثبّته بالامر:  py install 3.12
  echo       ^(لا تستخدم Python 3.14^)
  pause
  exit /b 1
)

REM تثبيت المكتبات اول مرة فقط ^(يتخطاها لو متثبتة^)
py -3.12 -c "import PyQt6" 2>nul || py -3.12 -m pip install -r requirements.txt

REM تشغيل البرنامج
py -3.12 main.py
if errorlevel 1 (
  echo.
  echo [خطأ] توقّف البرنامج. انسخ نص الخطأ بالاعلى وارسله.
  pause
)
