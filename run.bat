@echo off
cd /d "%~dp0"
python main_app.py
if errorlevel 1 pause
