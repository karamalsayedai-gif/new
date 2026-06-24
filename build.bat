@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion
title ShowroomERP - Build

echo ============================================================
echo            ShowroomERP  -  Build EXE
echo ============================================================
echo.

REM ---- Detect a working Python (prefer 3.12 / 3.13 / 3.11) ----
set "PYCMD="
for %%P in ("py -3.12" "py -3.13" "py -3.11" "py" "python") do (
  if not defined PYCMD (
    cmd /c %%~P --version >nul 2>&1
    if !errorlevel! EQU 0 set "PYCMD=%%~P"
  )
)

if not defined PYCMD (
  echo [ERROR] Python was not found on this PC.
  echo         Install Python 3.12 then run this file again:
  echo            py install 3.12
  echo         or download from https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

for /f "delims=" %%v in ('%PYCMD% --version') do echo [1/3] Using %%v   ^(command: %PYCMD%^)
echo.

echo [2/3] Installing required packages... ^(may take a minute^)
%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install -r requirements.txt
%PYCMD% -m pip install pyinstaller
if errorlevel 1 (
  echo.
  echo [ERROR] Package installation failed.
  echo         If it failed on PyQt6, install Python 3.12 ^(py install 3.12^)
  echo         and run this file again.
  pause
  exit /b 1
)
echo.

echo [3/3] Building the application...
%PYCMD% -m PyInstaller packaging\showroom_erp.spec --noconfirm
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. Copy the full error text above and send it.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   BUILD SUCCESSFUL
echo   App is ready at:
echo   %~dp0dist\ShowroomERP\ShowroomERP.exe
echo.
echo   To deploy: copy the whole folder  dist\ShowroomERP  to a USB drive.
echo ============================================================
echo.
explorer "%~dp0dist\ShowroomERP"
pause
