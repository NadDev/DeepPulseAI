@echo off
REM =====================================================
REM CRBOT - Start FastAPI Server (Local Development)
REM =====================================================

cd /d "%~dp0\backend"

echo.
echo ===============================================
echo 🚀 Starting CRBot FastAPI Server...
echo ===============================================
echo.

REM Load environment from .env.local
set PYTHONUNBUFFERED=1

REM Run the server
"%USERPROFILE%\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

echo.
echo API Documentation: http://localhost:8000/docs
echo.
