@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion
title ShowroomERP - Run

REM ---- Detect a working Python (prefer 3.12 / 3.13 / 3.11) ----
set "PYCMD="
for %%P in ("py -3.12" "py -3.13" "py -3.11" "py" "python") do (
  if not defined PYCMD (
    cmd /c %%~P --version >nul 2>&1
    if !errorlevel! EQU 0 set "PYCMD=%%~P"
  )
)

if not defined PYCMD (
  echo [ERROR] Python was not found. Install Python 3.12:  py install 3.12
  pause
  exit /b 1
)

REM Install dependencies on first run only (skipped if PyQt6 already present)
%PYCMD% -c "import PyQt6" 2>nul || %PYCMD% -m pip install -r requirements.txt

%PYCMD% main.py
if errorlevel 1 (
  echo.
  echo [ERROR] The app stopped. Copy the error text above and send it.
  pause
)
