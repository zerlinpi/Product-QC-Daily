@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto :fail
)
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto :fail
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe -m ruff check .
if errorlevel 1 goto :fail
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 goto :fail
set QT_QPA_PLATFORM=
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean Product-QC-Daily.spec
if errorlevel 1 goto :fail
echo Build ready: dist\Product-QC-Daily\Product-QC-Daily.exe
echo Keep the entire Product-QC-Daily directory together.
exit /b 0
:fail
echo Build failed. See the error above.
pause
exit /b 1
