@echo off
REM BioTrust - MongoDB Setup & Database Seeding

echo ============================================
echo BIOTRUST - MONGODB SETUP
echo ============================================
echo.

echo [PASSO 1] Verificar se MongoDB esta instalado...
echo.
where mongod >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    OK - MongoDB encontrado!
    echo.
) else (
    echo    AVISO - MongoDB nao encontrado
    echo.
    echo    Instalacao do MongoDB:
    echo    1. Download: https://www.mongodb.com/try/download/community
    echo    2. Escolher: Windows x64 MSI
    echo    3. Instalar com opcoes default
    echo.
    echo    OU usar Docker:
    echo    docker run -d -p 27017:27017 --name biotrust-mongo mongo:latest
    echo.
    pause
    exit /b 1
)

echo [PASSO 2] Verificar se MongoDB esta a correr...
echo.
timeout /t 2 /nobreak > nul
mongosh --eval "db.version()" --quiet >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    OK - MongoDB esta a correr!
    echo.
) else (
    echo    ERRO - MongoDB nao esta a correr
    echo.
    echo    Iniciar MongoDB:
    echo    - Servico: Executar 'net start MongoDB'
    echo    - Manual: Executar 'mongod' numa janela separada
    echo    - Docker: docker start biotrust-mongo
    echo.
    pause
    exit /b 1
)

echo [PASSO 3] Instalar dependencias Python...
echo.
pip install motor pymongo passlib[bcrypt] cryptography python-jose[cryptography] pydantic-settings
if %ERRORLEVEL% NEQ 0 (
    echo    ERRO ao instalar dependencias
    pause
    exit /b 1
)
echo    OK - Dependencias instaladas
echo.

echo [PASSO 4] Popular banco de dados com dados de teste...
echo.
python data\seed_database.py
if %ERRORLEVEL% NEQ 0 (
    echo    ERRO ao popular banco de dados
    pause
    exit /b 1
)

echo.
echo ============================================
echo SETUP COMPLETO!
echo ============================================
echo.
echo MongoDB esta configurado e populado com:
echo   - 5 utilizadores de teste
echo   - 12 merchants (Lisboa, Porto, Braga)
echo   - Cartoes encriptados
echo.
echo Podes verificar os dados:
echo   mongosh
echo   use biotrust
echo   db.users.find()
echo   db.merchants.find()
echo.
pause
