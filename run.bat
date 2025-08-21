@echo off
setlocal enabledelayedexpansion
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

REM Set virtual environment variables directly to avoid activation script errors
set "VIRTUAL_ENV=%SCRIPT_DIR%venv" 2>nul
set "PATH=%VIRTUAL_ENV%\Scripts;%PATH%" 2>nul
set "PYTHONPATH=%VIRTUAL_ENV%\Lib\site-packages;%PYTHONPATH%" 2>nul

echo Virtual environment activated

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found in virtual environment
    echo Please check your virtual environment setup
    pause
    exit /b 1
)

REM Run the Python script
echo Starting Python script...
python window_arranger.py

REM Check exit code
set "EXIT_CODE=%errorlevel%"

REM Clear virtual environment variables
set "VIRTUAL_ENV=" 2>nul
set "PYTHONPATH=" 2>nul

REM Show exit code to user
if %EXIT_CODE% equ 0 (
    echo Window Arranger completed successfully
) else (
    echo Window Arranger exited with error code: %EXIT_CODE%
)

echo.
echo Press any key to exit...
pause >nul 