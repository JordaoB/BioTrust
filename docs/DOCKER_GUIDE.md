# 🐳 BioTrust - Guia Docker

Este guia explica como usar Docker para executar o BioTrust em qualquer ambiente.

> **📝 Nota sobre Docker Compose v2:**  
> Este projeto usa Docker Compose v2+ (incluído no Docker Desktop moderno). O atributo `version:` foi removido dos ficheiros `docker-compose.yml` pois é obsoleto e ignorado nas versões recentes. Isto é **normal e esperado** - a versão é agora detectada automaticamente.

---

## 📋 Índice

- [Pré-requisitos](#-pré-requisitos)
- [Quick Start](#-quick-start)
- [Arquitetura Docker](#-arquitetura-docker)
- [Comandos Úteis](#-comandos-úteis)
- [Desenvolvimento](#-desenvolvimento)
- [Produção](#-produção)
- [Troubleshooting](#-troubleshooting)

---

## ✅ Pré-requisitos

### **Windows**
1. **Docker Desktop for Windows**
   - Download: https://docs.docker.com/desktop/windows/install/
   - Requisitos: Windows 10/11 Pro, Enterprise ou Education
   - Habilitar WSL 2 backend (recomendado)

2. **Verificar instalação:**
   ```powershell
   docker --version
   docker-compose --version
   ```

### **Linux**
1. **Docker Engine**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # Adicionar usuário ao grupo docker
   sudo usermod -aG docker $USER
   ```

2. **Docker Compose**
   ```bash
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

### **macOS**
1. **Docker Desktop for Mac**
   - Download: https://docs.docker.com/desktop/mac/install/
   - Funciona em Intel e Apple Silicon (M1/M2)

---

## 🚀 Quick Start

### **Método 1: Script Automático (Recomendado)**

#### **Windows:**
```powershell
.\scripts\docker-start.bat
```

#### **Linux/macOS:**
```bash
chmod +x scripts/docker-start.sh
./scripts/docker-start.sh
```

### **Método 2: Docker Compose Manual**

```bash
# 1. Build das imagens
docker-compose build

# 2. Iniciar containers
docker-compose up -d

# 3. Verificar status
docker-compose ps

# 4. Ver logs
docker-compose logs -f biotrust-api
```

### **Acesso:**
- 📡 **API:** http://localhost:8000
- 📚 **Swagger Docs:** http://localhost:8000/docs
- 🏥 **Health Check:** http://localhost:8000/health

---

## 🏗️ Arquitetura Docker

### **Containers**

```
┌────────────────────────────────────────┐
│         Host Machine (Windows)         │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │   Docker Network: biotrust-net   │ │
│  │                                  │ │
│  │  ┌────────────────────────────┐ │ │
│  │  │  Container: biotrust-api   │ │ │
│  │  │  - FastAPI Server          │ │ │
│  │  │  - Port: 8000              │ │ │
│  │  │  - Python 3.10-slim        │ │ │
│  │  │  - Health: /health         │ │ │
│  │  └────────────────────────────┘ │ │
│  │           ↕ volume mount         │ │
│  │  ┌────────────────────────────┐ │ │
│  │  │  Host: ./data/             │ │ │
│  │  │  Persistent data storage   │ │ │
│  │  └────────────────────────────┘ │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### **Volumes Montados**

| Volume | Propósito | Persistente |
|--------|-----------|-------------|
| `./data` | Transaction logs, statistics | ✅ Sim |
| `./logs` | Application logs | ✅ Sim |
| `./src` | Source code (dev) | ⚠️ Dev only |

### **Portas**

| Porta | Serviço | Protocolo |
|-------|---------|-----------|
| 8000 | API REST | HTTP |
| 8501 | Streamlit (opcional) | HTTP |

---

## 📦 Comandos Úteis

### **Gestão de Containers**

```bash
# Iniciar containers
docker-compose up -d

# Parar containers
docker-compose down

# Parar e remover volumes
docker-compose down -v

# Restart de um serviço específico
docker-compose restart biotrust-api

# Ver status
docker-compose ps
```

### **Logs e Debugging**

```bash
# Ver logs em tempo real
docker-compose logs -f

# Logs de um serviço específico
docker-compose logs -f biotrust-api

# Últimas 100 linhas
docker-compose logs --tail=100 biotrust-api

# Entrar no container (shell interativo)
docker exec -it biotrust-api bash

# Inspecionar container
docker inspect biotrust-api
```

### **Rebuild e Clean**

```bash
# Rebuild forçado (sem cache)
docker-compose build --no-cache

# Rebuild e restart
docker-compose up -d --build

# Remover imagens não utilizadas
docker image prune -a

# Limpar tudo (cuidado!)
docker system prune -a --volumes
```

### **Monitoramento**

```bash
# Uso de recursos
docker stats biotrust-api

# Processos rodando no container
docker top biotrust-api

# Health check manual
docker exec biotrust-api curl -f http://localhost:8000/health
```

---

## 🔧 Desenvolvimento

### **Hot Reload**

O container monta `./src` como volume, permitindo **hot reload**:

1. Edite qualquer ficheiro em `src/`
2. Uvicorn deteta mudanças automaticamente
3. API reinicia sem rebuild do container

**Exemplo:**
```bash
# Editar ficheiro
code src/api/api_server.py

# Ver logs do reload
docker-compose logs -f biotrust-api
# Output: INFO:     Watching for file changes
```

### **Debugger**

Para usar debugger Python (pdb):

```bash
# 1. Parar container detached
docker-compose down

# 2. Rodar em modo attached
docker-compose up

# 3. No código, adicionar:
import pdb; pdb.set_trace()

# 4. Interagir no terminal
```

### **Testes**

```bash
# Rodar testes dentro do container
docker exec -it biotrust-api python -m pytest tests/

# Com coverage
docker exec -it biotrust-api python -m pytest --cov=src tests/
```

---

## 🚀 Produção

### **Variáveis de Ambiente**

Crie `.env` na raiz:

```env
# API Configuration
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com

# Database (futuro)
DATABASE_URL=postgresql://user:pass@db:5432/biotrust

# Monitoring
SENTRY_DSN=your-sentry-dsn
```

### **Docker Compose Production**

```yaml
# docker-compose.prod.yml
# Note: 'version' attribute is no longer required in Docker Compose v2+

services:
  biotrust-api:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=production
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

**Iniciar:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### **Deploy em Cloud**

#### **AWS ECS**
```bash
# 1. Build e push para ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t biotrust-api .
docker tag biotrust-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/biotrust-api:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/biotrust-api:latest

# 2. Deploy via ECS Task Definition
aws ecs update-service --cluster biotrust --service api --force-new-deployment
```

#### **Azure Container Instances**
```bash
# 1. Build e push para ACR
az acr login --name biotrust
docker build -t biotrust-api .
docker tag biotrust-api biotrust.azurecr.io/biotrust-api:latest
docker push biotrust.azurecr.io/biotrust-api:latest

# 2. Deploy
az container create \
  --resource-group BioTrust \
  --name biotrust-api \
  --image biotrust.azurecr.io/biotrust-api:latest \
  --ports 8000 \
  --cpu 2 --memory 4
```

---

## 🐛 Troubleshooting

### **Warning: "the attribute `version` is obsolete"**

**Sintoma:**
```
level=warning msg="docker-compose.yml: the attribute `version` is obsolete"
```

**Solução:**
✅ **Isto NÃO é um erro!** É apenas um aviso informativo.

O Docker Compose v2+ (incluído no Docker Desktop moderno) não requer mais o atributo `version:` nos ficheiros `docker-compose.yml`. A versão é detectada automaticamente.

**Ação:** Nenhuma necessária. O warning pode ser ignorado ou, se preferires, remove a linha `version: 'x.x'` do teu `docker-compose.yml`.

---

### **Problema: Container não inicia**

```bash
# Ver logs detalhados
docker-compose logs biotrust-api

# Verificar se porta está ocupada
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/macOS

# Inspecionar saúde
docker inspect biotrust-api | grep -A 10 Health
```

### **Problema: "Cannot connect to Docker daemon"**

**Windows:**
1. Abrir Docker Desktop
2. Aguardar inicialização completa
3. Verificar: `docker ps`

**Linux:**
```bash
# Iniciar Docker service
sudo systemctl start docker

# Enable on boot
sudo systemctl enable docker

# Adicionar usuário ao grupo
sudo usermod -aG docker $USER
```

### **Problema: Imagem muito grande**

```bash
# Ver tamanho da imagem
docker images biotrust-api

# Otimizar:
# 1. Multi-stage build
# 2. Usar alpine em vez de slim
# 3. Limpar cache no Dockerfile
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
```

### **Problema: Performance lenta**

```bash
# Verificar recursos
docker stats biotrust-api

# Ajustar limites em docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

### **Problema: Hot reload não funciona**

**Windows WSL 2:**
```bash
# Adicionar ao docker-compose.yml:
environment:
  - WATCHFILES_FORCE_POLLING=true
```

---

## 📊 Monitoramento e Logs

### **Estrutura de Logs**

```
logs/
├── api.log          # API access logs
├── errors.log       # Error logs
└── transactions.log # Transaction audit trail
```

### **Configurar Logging**

```python
# src/api/api_server.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/api.log'),
        logging.StreamHandler()
    ]
)
```

### **Agregação de Logs (futuro)**

- **ELK Stack:** Elasticsearch + Logstash + Kibana
- **Grafana Loki:** Lightweight log aggregation
- **CloudWatch Logs:** Para AWS
- **Azure Monitor:** Para Azure

---

## 🔒 Segurança

### **Best Practices**

1. **Não rodar como root:**
   ```dockerfile
   RUN useradd -m -u 1000 biotrust
   USER biotrust
   ```

2. **Escanear vulnerabilidades:**
   ```bash
   docker scan biotrust-api
   ```

3. **Secrets management:**
   ```bash
   # Usar Docker secrets (Swarm)
   echo "my_secret_key" | docker secret create api_key -
   ```

4. **Network isolation:**
   ```yaml
   # docker-compose.yml
   networks:
     biotrust-network:
       driver: bridge
       internal: true  # Sem acesso externo
   ```

---

## 🎯 Próximos Passos

- [ ] Adicionar PostgreSQL container
- [ ] Implementar Redis para caching
- [ ] Configurar Nginx reverse proxy
- [ ] CI/CD com GitHub Actions
- [ ] Kubernetes manifests (K8s)
- [ ] Helm charts para deploy
- [ ] Prometheus + Grafana monitoring

---

## 📚 Recursos

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [FastAPI in Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

<div align="center">

**🐳 Developed with Docker by BioTrust Team**

*Making deployment as smooth as authentication*

</div>
