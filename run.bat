@echo off
REM chcp 65001 >nul
echo Starting Window Arranger...

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists and is valid
if not exist "venv" (
    echo Virtual environment not found, please run setup_and_run.bat first
    pause
    exit /b 1
)

REM Check if virtual environment is valid by testing activation
call venv\Scripts\activate.bat >nul 2>&1
if errorlevel 1 (
    echo Virtual environment is corrupted or invalid
    echo Removing old virtual environment...
    rmdir /s /q venv
    echo Please run setup_and_run.bat to recreate virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment and run
call venv\Scripts\activate.bat
python window_arranger.py

REM Deactivate virtual environment after Python script exits
call venv\Scripts\deactivate.bat

pause 