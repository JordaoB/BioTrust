# BioTrust - Dockerfile para API REST
# Python 3.10 slim para reduzir tamanho da imagem
FROM python:3.10-slim

# Metadata
LABEL maintainer="BioTrust Team - TecStorm '26"
LABEL description="BioTrust API - Biometric Authentication with Liveness Detection"
LABEL version="1.0.0"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema necessárias para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (para cache de layers)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY src/ ./src/
COPY data/ ./data/

# Criar diretórios necessários
RUN mkdir -p /app/data /app/logs

# Expor porta da API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Comando padrão - rodar API server
CMD ["python", "-m", "uvicorn", "src.api.api_server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
