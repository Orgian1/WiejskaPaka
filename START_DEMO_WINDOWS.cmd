@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if exist ".venv-demo\Scripts\python.exe" goto ready
where py >nul 2>nul
if errorlevel 1 goto pythonfallback
py -3.12 -m venv .venv-demo
if not errorlevel 1 goto install
:pythonfallback
python -m venv .venv-demo
if errorlevel 1 goto failed
:install
:ready
".venv-demo\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 goto failed
".venv-demo\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
".venv-demo\Scripts\python.exe" scripts\check_approved_ui.py
if errorlevel 1 goto failed
".venv-demo\Scripts\python.exe" scripts\run_phone_demo.py --full-demo --port 8766
if "%ERRORLEVEL%"=="130" exit /b 0
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Nie udalo sie uruchomic demo. Zachowaj komunikat bledu z tego okna.
echo Wymagany Python 3.12 oraz internet przy pierwszej instalacji.
pause
exit /b 1
