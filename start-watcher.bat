@echo off
cd /d "%~dp0"
if exist "%~dp0python\python.exe" (
    cd /d "%~dp0backend"
    "%~dp0python\python.exe" watcher/gamelog_watcher.py
) else (
    call venv\Scripts\activate.bat
    cd backend
    python watcher/gamelog_watcher.py
)
pause
