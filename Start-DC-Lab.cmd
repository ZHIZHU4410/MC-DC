@echo off
python "%~dp0tools\start_dc_lab.py" --launch
if errorlevel 1 pause
