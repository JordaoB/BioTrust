@echo off
echo ========================================
echo    BioTrust Web Interface
echo    Starting Streamlit Frontend...
echo ========================================
echo.
echo Web interface will open in your browser
echo URL: http://localhost:8501
echo.
echo Make sure API server is running first!
echo.

.\venv310\Scripts\streamlit run web\streamlit\web_app.py

pause
