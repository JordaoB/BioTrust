@echo off
REM BioTrust - Script de inicialização Docker (Windows)

echo ========================================
echo    BioTrust - Docker Startup Script
echo ========================================
echo.

REM Verificar se Docker está instalado
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Docker nao esta instalado!
    echo Instale: https://docs.docker.com/desktop/windows/install/
    pause
    exit /b 1
)

echo [OK] Docker instalado
echo.

REM Parar containers existentes
echo [INFO] Parando containers existentes...
docker-compose down 2>nul

REM Build das imagens
echo.
echo [INFO] Building Docker images...
docker-compose build

REM Iniciar containers
echo.
echo [INFO] Iniciando containers...
docker-compose up -d

REM Aguardar API estar pronta
echo.
echo [INFO] Aguardando API ficar disponivel...
timeout /t 5 /nobreak >nul

REM Verificar saúde da API
powershell -Command "try { Invoke-RestMethod -Uri http://localhost:8000/health -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo.
    echo [ERRO] API nao respondeu. Verificando logs...
    docker-compose logs biotrust-api
    pause
    exit /b 1
)

echo.
echo [OK] API esta rodando!
echo.
echo ========================================
echo    URLs disponiveis:
echo ========================================
echo    - API: http://localhost:8000
echo    - Docs: http://localhost:8000/docs
echo    - Health: http://localhost:8000/health
echo.
echo ========================================
echo    Comandos uteis:
echo ========================================
echo    - Ver logs: docker-compose logs -f
echo    - Parar: docker-compose down
echo    - Restart: docker-compose restart
echo.
echo [INFO] Pressione Ctrl+C para sair
echo.

REM Exibir logs
docker-compose logs -f
