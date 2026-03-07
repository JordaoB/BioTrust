@echo off
REM BioTrust - Popular MongoDB (assumindo que ja esta a correr)

echo ============================================
echo BIOTRUST - POPULAR DATABASE
echo ============================================
echo.

echo Verificando se MongoDB esta acessivel...
echo.

REM Instalar dependencias primeiro
echo [1/2] Instalar dependencias Python...
pip install -q motor pymongo passlib[bcrypt] cryptography python-jose[cryptography] pydantic-settings geopy
if %ERRORLEVEL% NEQ 0 (
    echo    [ERRO] Falha ao instalar dependencias
    pause
    exit /b 1
)
echo    OK - Dependencias instaladas
echo.

REM Popular database
echo [2/2] Popular database com dados de teste...
echo.
python data\seed_database.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo SUCESSO! DATABASE POPULADA
    echo ============================================
    echo.
    echo MongoDB: mongodb://localhost:27017
    echo Database: biotrust
    echo.
    echo Dados criados:
    echo   - 5 utilizadores de teste
    echo   - 12 merchants em Lisboa, Porto, Braga
    echo   - Cartoes encriptados
    echo.
    echo Login de teste:
    echo   Email: joao.silva@example.com
    echo   Password: password123
    echo.
) else (
    echo.
    echo ============================================
    echo ERRO AO POPULAR DATABASE
    echo ============================================
    echo.
    echo MongoDB pode nao estar a correr.
    echo.
    echo Verifica:
    echo   1. MongoDB Compass esta aberto?
    echo   2. Consegues ver "localhost:27017" no Compass?
    echo.
    echo Se MongoDB NAO esta a correr:
    echo   - Abre MongoDB Compass
    echo   - OU inicia servico: net start MongoDB
    echo   - OU Docker: docker start biotrust-mongo
    echo.
)

pause
