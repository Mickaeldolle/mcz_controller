@echo off
cd /d "%~dp0"
title MCZ - Essai d'appairage unique
".venv\Scripts\python.exe" -u tools\pair_once.py --port COM3
pause
