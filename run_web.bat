@echo off
REM UCU Study Room Reservation System - Web Application Launcher (Windows)
REM This script activates the virtual environment and runs the Flask web application

echo ========================================
echo UCU Study Room Reservation System
echo Starting Web Application...
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first with: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)

REM Run the Flask application
echo Starting Flask application...
echo.
python app.py

REM If the script exits, pause to see any error messages
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)

