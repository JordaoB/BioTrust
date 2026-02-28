#!/bin/bash
# BioTrust - Docker Test Script
# Testa o build e funcionamento básico do Docker

echo "🧪 BioTrust Docker Test Script"
echo "=============================="
echo ""

# Test 1: Docker instalado?
echo "[1/5] Verificando Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ FAIL: Docker não está instalado"
    exit 1
fi
echo "✅ PASS: Docker instalado"

# Test 2: Docker Compose instalado?
echo "[2/5] Verificando Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ FAIL: Docker Compose não está instalado"
    exit 1
fi
echo "✅ PASS: Docker Compose instalado"

# Test 3: Build da imagem
echo "[3/5] Building Docker image..."
if docker build -t biotrust-api-test . > /dev/null 2>&1; then
    echo "✅ PASS: Build successful"
else
    echo "❌ FAIL: Build failed"
    exit 1
fi

# Test 4: Iniciar container
echo "[4/5] Starting container..."
if docker run -d --name biotrust-test -p 8001:8000 biotrust-api-test > /dev/null 2>&1; then
    echo "✅ PASS: Container started"
else
    echo "❌ FAIL: Container failed to start"
    docker logs biotrust-test
    exit 1
fi

# Aguardar API ficar pronta
sleep 5

# Test 5: Health check
echo "[5/5] Testing health endpoint..."
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ PASS: API respondeu health check"
else
    echo "❌ FAIL: API não respondeu"
    docker logs biotrust-test
    docker stop biotrust-test
    docker rm biotrust-test
    docker rmi biotrust-api-test
    exit 1
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
docker stop biotrust-test > /dev/null 2>&1
docker rm biotrust-test > /dev/null 2>&1
docker rmi biotrust-api-test > /dev/null 2>&1

echo ""
echo "✅ All tests passed!"
echo "Docker setup is working correctly."
