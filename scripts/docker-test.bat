@echo off
REM BioTrust - Docker Test Script (Windows)
REM Testa o build e funcionamento básico do Docker

echo ====================================
echo    BioTrust Docker Test Script
echo ====================================
echo.

REM Test 1: Docker instalado?
echo [1/5] Verificando Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker nao esta instalado
    exit /b 1
)
echo [PASS] Docker instalado
echo.

REM Test 2: Docker Compose instalado?
echo [2/5] Verificando Docker Compose...
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker Compose nao esta instalado
    exit /b 1
)
echo [PASS] Docker Compose instalado
echo.

REM Test 3: Build da imagem
echo [3/5] Building Docker image...
docker build -t biotrust-api-test . >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Build failed
    exit /b 1
)
echo [PASS] Build successful
echo.

REM Test 4: Iniciar container
echo [4/5] Starting container...
docker run -d --name biotrust-test -p 8001:8000 biotrust-api-test >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Container failed to start
    docker logs biotrust-test
    exit /b 1
)
echo [PASS] Container started
echo.

REM Aguardar API ficar pronta
echo Aguardando API...
timeout /t 5 /nobreak >nul

REM Test 5: Health check
echo [5/5] Testing health endpoint...
powershell -Command "try { Invoke-RestMethod -Uri http://localhost:8001/health -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo [FAIL] API nao respondeu
    docker logs biotrust-test
    docker stop biotrust-test
    docker rm biotrust-test
    docker rmi biotrust-api-test
    exit /b 1
)
echo [PASS] API respondeu health check
echo.

REM Cleanup
echo ====================
echo    Cleaning up...
echo ====================
docker stop biotrust-test >nul 2>&1
docker rm biotrust-test >nul 2>&1
docker rmi biotrust-api-test >nul 2>&1

echo.
echo ====================================
echo    All tests passed!
echo    Docker setup is working correctly.
echo ====================================
pause
