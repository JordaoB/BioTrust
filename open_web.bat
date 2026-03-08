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

start http://localhost:8000/web

echo.
echo Browser opened! If the API is not running, use:
echo    python -m uvicorn backend.main:app --reload
echo.
pause
