@echo off
chcp 65001 >nul
title Build MDavariVPN.exe
cd /d "%~dp0"

echo === 1/3 نصب PyInstaller ===
python -m pip install --upgrade pip pyinstaller || goto :err

echo === 2/3 ساخت فایل اجرایی ===
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name MDavariVPN ^
  --icon "app\ui\icon.ico" ^
  --add-data "app;app" ^
  main.py || goto :err

echo === 3/3 پایان ===
echo.
echo فایل اجرایی ساخته شد:  dist\MDavariVPN.exe
explorer dist
pause
exit /b 0

:err
echo.
echo [X] ساخت ناموفق بود. متن خطا را برای من بفرست.
pause
exit /b 1
