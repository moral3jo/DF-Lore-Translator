@echo off
title DF Traductor - Panel de Gestion
cd /d "%~dp0backend"
echo.
echo  DF Traductor - Panel de gestion
echo  http://localhost:5200
echo.
python admin/app.py
pause
