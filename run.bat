@echo off
cd /d "%~dp0"
title Bao duong thiet bi - May chu
set PYTHONUTF8=1
chcp 65001 >nul

if not exist "venv\Scripts\python.exe" (
    echo [Loi] Khong tim thay moi truong Python "venv".
    echo Hay chay setup.bat truoc.
    pause
    exit /b 1
)

start "" /min cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8899/"

echo Dang khoi dong may chu... (dong cua so nay de tat ung dung)
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8899

pause
