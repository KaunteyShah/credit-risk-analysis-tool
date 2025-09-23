@echo off
REM Credit Risk Analysis - Quick Start Script for Windows

echo 🚀 Credit Risk Analysis - Quick Start
echo ======================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.11+ first.
    pause
    exit /b 1
)

echo 🔧 Setting up virtual environment...

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo ⚡ Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip and install requirements
echo 📥 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Run verification
echo 🔍 Verifying setup...
python verify_setup.py

if %errorlevel% equ 0 (
    echo.
    echo 🎉 Setup complete! Starting the application...
    echo 🌐 The app will be available at: http://localhost:8000
    echo.
    python main.py
) else (
    echo ❌ Setup verification failed. Please check the errors above.
    pause
    exit /b 1
)

pause
