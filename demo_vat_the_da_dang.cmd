@echo off
cd /d "%~dp0"
".venv-yolo\Scripts\python.exe" tools\run_live_demo.py --scenario objects_room --vision-config config\vision_objects.json
