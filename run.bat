@echo off
setlocal enabledelayedexpansion
title AegisBot WhatsApp Business AI

echo =====================================================================
echo    AegisBot -- AI WhatsApp Business Operating System ^& Lead Engine
echo =====================================================================
echo.

REM 1. Check for .env file
if not exist "%~dp0.env" (
    echo [!] .env file not found. Copying from .env.example...
    copy "%~dp0.env.example" "%~dp0.env" >nul
    echo [*] Created .env from template.
    echo [*] Please ensure your GROQ_API_KEY and SUPABASE keys are filled in .env
    echo.
)

REM 2. Detect Python executable
set "PY_CMD="
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
) else (
    py -3 --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py -3"
    ) else (
        if exist "C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" (
            set "PY_CMD=C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python 3.10+ not found in PATH or standard directories!
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [*] Using Python: %PY_CMD%

REM 3. Check requirements
echo [*] Checking dependencies...
%PY_CMD% -c "import fastapi, uvicorn, supabase, groq, reportlab" >nul 2>&1
if !errorlevel! neq 0 (
    echo [*] Installing required packages from requirements.txt...
    %PY_CMD% -m pip install -r "%~dp0requirements.txt"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo [OK] Environment and dependencies verified.
echo.
echo =====================================================================
echo    Launching AegisBot Server on http://localhost:8000
echo    Web Dashboard: http://localhost:8000
echo    Health Endpoint: http://localhost:8000/health
echo    Press CTRL+C anytime to stop the server
echo =====================================================================
echo.

REM 4. Launch browser after a brief pause in background
start "" "%~dp0" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

REM 5. Run Uvicorn Server
%PY_CMD% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
