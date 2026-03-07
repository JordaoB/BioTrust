@echo off
REM BioTrust - Script de Limpeza
REM Remove arquivos desnecessarios (demos, testes, codigo antigo)

echo ============================================
echo BIOTRUST - LIMPEZA DE CODIGO
echo ============================================
echo.

echo [1/9] Removendo demos...
rmdir /S /Q demos 2>nul
echo     OK - demos/ removido

echo [2/9] Removendo God Mode Dashboard e cenarios...
del /Q src\apps\god_mode_dashboard.py 2>nul
del /Q src\apps\demo_scenarios.py 2>nul
del /Q src\apps\roi_calculator.py 2>nul
del /Q src\apps\transaction_log.json 2>nul
echo     OK - demos apps removidos

echo [3/9] Removendo web antigo...
rmdir /S /Q web 2>nul
echo     OK - web/ removido

echo [4/9] Removendo documentacao de marketing...
del /Q docs\B2B_ONE_PAGER.md 2>nul
del /Q docs\INTEGRATION_EXAMPLES.md 2>nul
del /Q docs\SCIENTIFIC_VALIDATION.md 2>nul
del /Q docs\TESTE_COMPLETO.md 2>nul
echo     OK - docs marketing removidos

echo [5/9] Removendo liveness detector antigo (V1)...
del /Q src\core\liveness_detector.py 2>nul
echo     OK - liveness_detector.py V1 removido

echo [6/9] Removendo transaction logger simples...
del /Q src\core\transaction_logger.py 2>nul
echo     OK - transaction_logger.py removido

echo [7/9] Removendo API e payment system antigos...
del /Q src\api\api_server.py 2>nul
del /Q src\payment_system.py 2>nul
echo     OK - APIs antigas removidas

echo [8/9] Removendo scripts antigos de launcher...
rmdir /S /Q scripts 2>nul
echo     OK - scripts/ removido

echo [9/9] Removendo logs e cache...
del /Q transaction_log.json 2>nul
del /Q data\transaction_log.json 2>nul
rmdir /S /Q __pycache__ 2>nul
rmdir /S /Q src\__pycache__ 2>nul
rmdir /S /Q src\core\__pycache__ 2>nul
rmdir /S /Q src\apps\__pycache__ 2>nul
rmdir /S /Q src\api\__pycache__ 2>nul
echo     OK - cache limpo

echo.
echo ============================================
echo LIMPEZA COMPLETA!
echo ============================================
echo.
echo Arquivos mantidos:
echo   - src/core/liveness_detector_v2.py (SISTEMA ANTI-SPOOFING)
echo   - src/core/risk_engine.py (MOTOR DE RISCO)
echo   - src/core/passive_liveness.py (rPPG DETECTOR)
echo   - requirements.txt, LICENSE, README.md
echo.
echo Proximos passos:
echo   1. Configurar MongoDB
echo   2. Criar novo backend (FastAPI)
echo   3. Criar frontend interativo com mapa
echo.
pause
