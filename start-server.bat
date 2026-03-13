@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
cd backend
python api/app.py
pause
