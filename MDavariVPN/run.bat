@echo off
chcp 65001 >nul
title MDavari VPN PRO - Smart SSTP Client
cd /d "%~dp0"

set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" (where python >nul 2>nul && set PY=python)
if "%PY%"=="" (
  echo.
  echo [X] Python روی این ویندوز پیدا نشد.
  echo     از سایت python.org نسخه 3.10 یا بالاتر را نصب کن
  echo     و هنگام نصب تیک "Add python.exe to PATH" را بزن.
  echo.
  pause
  exit /b 1
)

%PY% "%~dp0main.py" %*
if errorlevel 1 pause
