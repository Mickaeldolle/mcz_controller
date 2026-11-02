@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m app.launch --serial-port COM3
if errorlevel 1 pause
