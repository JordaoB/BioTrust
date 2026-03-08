@echo off
REM =========================================
REM BioTrust - Open Web Interface
REM =========================================
echo.
echo ========================================
echo  BioTrust - Web Interface
echo ========================================
echo.
echo Starting browser...
echo.

start http://localhost:8000/static/login.html

echo.
echo Browser opened! If the API is not running, use:
echo    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
echo.
pause
