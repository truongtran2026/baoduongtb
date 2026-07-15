@echo off
cd /d "%~dp0"
title Bao duong thiet bi - Cai dat

echo Dang tao moi truong Python...
py -m venv venv
if errorlevel 1 (
    echo [Loi] Khong tim thay Python. Hay cai Python 3.10+ tu python.org roi chay lai file nay.
    pause
    exit /b 1
)

echo Dang cai thu vien can thiet...
venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo.
echo Xong! Chay file run.bat de mo ung dung.
pause
