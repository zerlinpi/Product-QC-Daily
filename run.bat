@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto :fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :fail
.venv\Scripts\pythonw.exe -m app.main
exit /b 0
:fail
echo Failed. Install Python 3.12 or use the packaged Windows application.
pause
exit /b 1
