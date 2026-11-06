@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-yolo\Scripts\python.exe" (
  echo Chua co moi truong .venv-yolo. Xem docs\ego-vision.md
  pause
  exit /b 1
)
".venv-yolo\Scripts\python.exe" tools\run_live_demo.py
if errorlevel 1 pause
