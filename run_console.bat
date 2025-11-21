@echo off
REM UCU Study Room Reservation System - Console Application Launcher (Windows)
REM This script activates the virtual environment and runs the console application

echo ========================================
echo UCU Study Room Reservation System
echo Starting Console Application...
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

REM Run the console application
echo Starting console application...
echo.
python main.py

REM Pause to see any messages before closing
pause

