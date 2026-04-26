@echo off
echo ===================================================
echo 🚀 Starting Goofy Desktop Agent...
echo ===================================================

:: 1. Clean up old instances
echo [System] Cleaning up old processes...
taskkill /F /IM pythonw.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: 3. Start the Goofy Backend Engine (FastAPI)
echo [System] Launching AI Brain (FastAPI)...
cd /d "%~dp0..\backend"
if exist ".venv\Scripts\python.exe" (
    start /B .venv\Scripts\python -m uvicorn app.main:app --port 8000 >nul 2>&1
) else if exist "venv\Scripts\python.exe" (
    start /B venv\Scripts\python -m uvicorn app.main:app --port 8000 >nul 2>&1
) else (
    start /B python -m uvicorn app.main:app --port 8000 >nul 2>&1
)

:: Give Backend a moment to start
timeout /t 3 /nobreak >nul

:: 4. Start the Goofy Python UI Engine
echo [System] Launching Goofy Background Engine...
cd /d "%~dp0"
start /MIN .\venv\Scripts\python main.py

echo.
echo ✅ Setup Complete! Goofy is now running.
echo    Say "Hello Goofy" to wake him up!
echo.
pause
