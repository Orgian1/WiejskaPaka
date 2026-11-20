@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto unpack
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist "requirements-lock.txt" goto unpack
if not exist "scripts\run_phone_demo.py" goto unpack
if not exist "backend\app.py" goto unpack

set "demo_python=.venv-demo\Scripts\python.exe"
set "check_version=import sys; sys.exit(sys.version_info[:2] != (3, 12))"
if not exist "%demo_python%" goto find_python
"%demo_python%" -c "%check_version%" >nul 2>&1
if not errorlevel 1 goto prepare_pip

:find_python
py -3.12 -c "%check_version%" >nul 2>&1
if not errorlevel 1 goto create_with_py
python -c "%check_version%" >nul 2>&1
if errorlevel 1 goto missing_python
set "python_command=python"
goto create_environment

:create_with_py
set "python_command=py -3.12"

:create_environment
set "stage=tworzenie srodowiska Python"
%python_command% -m venv --without-pip .venv-demo
if errorlevel 1 goto failed

:prepare_pip
"%demo_python%" -m pip --version >nul 2>&1
if not errorlevel 1 goto install
set "stage=przygotowanie pip"
"%demo_python%" -m ensurepip --upgrade --default-pip
if errorlevel 1 goto failed

:install
set "stage=instalacja i kontrola pakietow"
"%demo_python%" -m pip install -r requirements-lock.txt
if errorlevel 1 goto failed
"%demo_python%" -m pip check
if errorlevel 1 goto failed
set "stage=kontrola zatwierdzonego widoku"
"%demo_python%" scripts\check_approved_ui.py
if errorlevel 1 goto failed
set "stage=uruchamianie aplikacji"
"%demo_python%" scripts\run_phone_demo.py --full-demo --port 8766
if "%ERRORLEVEL%"=="130" exit /b 0
if errorlevel 1 goto failed
exit /b 0

:unpack
echo Rozpakuj caly ZIP przez "Wyodrebnij wszystkie", a nastepnie otworz
echo START_DEMO_WINDOWS.cmd z folderu, w ktorym sa tez foldery scripts i backend.
pause
exit /b 1

:missing_python
echo Nie wykryto dzialajacego Pythona 3.12. Zainstaluj Python 3.12
echo z opcja dodania do PATH lub z Python Launcher i uruchom skrypt ponownie.
pause
exit /b 1

:failed
echo.
echo Nie udalo sie uruchomic demo. Etap: %stage%.
echo Zachowaj komunikat bledu z tego okna.
pause
exit /b 1
