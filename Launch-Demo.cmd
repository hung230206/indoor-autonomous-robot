@echo off
cd /d "%~dp0"
python run.py demo --gui
if errorlevel 1 pause
