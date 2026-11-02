@echo off
cd /d "%~dp0"
title MCZ - Trames recues en direct
".venv\Scripts\python.exe" -u tools\monitor_serial.py --port COM3 %*
if errorlevel 1 pause
