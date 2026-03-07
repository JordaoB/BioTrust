@echo off
REM BioTrust - MongoDB Local Installer (Windows)

echo ============================================
echo MONGODB - INSTALACAO LOCAL
echo ============================================
echo.

echo Este script vai:
echo   1. Criar pasta de dados do MongoDB
echo   2. Iniciar MongoDB localmente
echo   3. Popular database com dados de teste
echo.

REM Verificar se MongoDB esta instalado
where mongod >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] MongoDB nao esta instalado!
    echo.
    echo Opcoes:
    echo.
    echo   A] DOCKER - recomendado:
    echo      1. Abrir Docker Desktop
    echo      2. Esperar ficar verde
    echo      3. Executar: docker run -d -p 27017:27017 --name biotrust-mongo mongo:latest
    echo.
    echo   B] INSTALACAO LOCAL:
    echo      1. Download: https://www.mongodb.com/try/download/community
    echo      2. Escolher: Windows x64 MSI
    echo      3. Instalar como servico Windows
    echo      4. Executar este script novamente
    echo.
    echo   C] MONGODB PORTABLE - sem admin:
    echo      1. Download ZIP: https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-7.0.7.zip
    echo      2. Extrair para: C:\mongodb
    echo      3. Executar este script novamente
    echo.
    pause
    exit /b 1
)

echo [OK] MongoDB encontrado!
echo.

REM Criar pasta de dados
if not exist "mongodb_data" (
    echo [1/4] Criar pasta de dados...
    mkdir mongodb_data
    echo       OK - mongodb_data\ criada
) else (
    echo [1/4] Pasta de dados ja existe
)
echo.

REM Verificar se ja esta a correr
echo [2/4] Verificar se MongoDB ja esta a correr...
timeout /t 1 /nobreak > nul
mongosh --eval "db.version()" --quiet >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo       OK - MongoDB ja esta ativo
) else (
    echo       Iniciar MongoDB...
    start "MongoDB Server" mongod --dbpath=mongodb_data --port=27017
    echo       Aguardar 5 segundos para inicializacao...
    timeout /t 5 /nobreak > nul
)
echo.

REM Verificar conexao
echo [3/4] Testar conexao...
mongosh --eval "db.version()" --quiet >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo       [ERRO] Nao foi possivel conectar ao MongoDB
    echo       Tenta:
    echo         - Verificar se porta 27017 esta livre
    echo         - Executar: mongod --dbpath=mongodb_data
    pause
    exit /b 1
)
echo       OK - Conectado com sucesso!
echo.

REM Instalar dependencias e popular database
echo [4/4] Popular database com dados de teste...
echo.
pip install motor pymongo passlib[bcrypt] cryptography python-jose[cryptography] pydantic-settings geopy >nul 2>nul
python data\seed_database.py

echo.
echo ============================================
echo MONGODB CONFIGURADO COM SUCESSO!
echo ============================================
echo.
echo MongoDB esta a correr em: mongodb://localhost:27017
echo Database: biotrust
echo.
echo Para parar MongoDB: Fechar janela "MongoDB Server"
echo Para reiniciar: Executar este script novamente
echo.
echo Verificar dados:
echo   mongosh
echo   use biotrust
echo   db.users.find()
echo.
pause
