@echo off
echo ========================================
echo    BioTrust - Complete System Launch
echo ========================================
echo.
echo This will start:
echo  1. FastAPI Backend Server
echo  2. Streamlit Web Interface
echo.
echo Both will run in separate windows.
echo.
pause

echo.
echo [1/2] Starting API Server...
start "BioTrust API Server" cmd /k .\venv310\Scripts\python.exe src\api\api_server.py

echo Waiting 5 seconds for API to initialize...
timeout /t 5 /nobreak > nul

echo.
echo [2/2] Starting Web Interface...
start "BioTrust Web Interface" cmd /k .\venv310\Scripts\streamlit run web\streamlit\web_app.py

echo.
echo ========================================
echo    System Started!
echo ========================================
echo.
echo API Server: http://localhost:8000/docs
echo Web Interface: http://localhost:8501
echo.
echo Press any key to exit this launcher...
echo (The servers will keep running)
pause > nul
