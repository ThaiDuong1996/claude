@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai dat Lucifer ===
where python >nul 2>nul || (echo Chua cai Python. Tai tai https://www.python.org/downloads/ va tick "Add python.exe to PATH". & pause & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env >nul
echo.
echo Xong! Mo file .env de dien ANTHROPIC_API_KEY (neu co), roi chay run.bat
pause
