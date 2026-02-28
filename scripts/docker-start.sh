#!/bin/bash
# BioTrust - Script de inicialização Docker (Linux/macOS)

echo "🐳 BioTrust - Docker Startup Script"
echo "===================================="
echo ""

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado!"
    echo "Instale: https://docs.docker.com/get-docker/"
    exit 1
fi

# Verificar se Docker Compose está disponível
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não está instalado!"
    echo "Instale: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker instalado"
echo ""

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose down 2>/dev/null

# Build das imagens
echo ""
echo "🔨 Building Docker images..."
docker-compose build

# Iniciar containers
echo ""
echo "🚀 Iniciando containers..."
docker-compose up -d

# Aguardar API estar pronta
echo ""
echo "⏳ Aguardando API ficar disponível..."
sleep 5

# Verificar saúde da API
if curl -f http://localhost:8000/health &> /dev/null; then
    echo ""
    echo "✅ API está rodando!"
    echo ""
    echo "📡 URLs disponíveis:"
    echo "   - API: http://localhost:8000"
    echo "   - Docs: http://localhost:8000/docs"
    echo "   - Health: http://localhost:8000/health"
    echo ""
    echo "📋 Comandos úteis:"
    echo "   - Ver logs: docker-compose logs -f"
    echo "   - Parar: docker-compose down"
    echo "   - Restart: docker-compose restart"
    echo ""
else
    echo "❌ API não respondeu. Verificando logs..."
    docker-compose logs biotrust-api
    exit 1
fi

# Exibir logs
echo "📋 Exibindo logs (Ctrl+C para sair):"
echo ""
docker-compose logs -f
