# BioTrust - Nova Estrutura do Projeto

## 🧹 Limpeza Realizada

### Removido:
- ❌ `demos/` - Demos de apresentação
- ❌ `src/apps/god_mode_dashboard.py` - Dashboard de demonstração  
- ❌ `src/apps/demo_scenarios.py` - Cenários fake
- ❌ `src/apps/roi_calculator.py` - Calculadora demo
- ❌ `web/` - Interfaces antigas
- ❌ `src/core/liveness_detector.py` - Versão V1 antiga
- ❌ `src/core/transaction_logger.py` - Logger simples
- ❌ `src/api/api_server.py` - API antiga
- ❌ `src/payment_system.py` - Sistema antigo
- ❌ `docs/B2B_ONE_PAGER.md`, `INTEGRATION_EXAMPLES.md`, etc - Docs marketing

### Mantido (Core):
- ✅ `src/core/liveness_detector_v2.py` - Sistema anti-spoofing com 6 camadas
- ✅ `src/core/risk_engine.py` - Motor de análise de risco
- ✅ `src/core/passive_liveness.py` - Detector rPPG
- ✅ `requirements.txt` - Dependências
- ✅ `LICENSE`, `README.md` - Documentação base

---

## 🏗️ Nova Estrutura (A Construir)

```
BioTrust/
│
├── backend/                          # Novo backend FastAPI
│   ├── __init__.py
│   ├── main.py                       # FastAPI app principal
│   ├── config.py                     # Configuração (MongoDB, secrets)
│   │
│   ├── models/                       # Modelos MongoDB (Pydantic)
│   │   ├── __init__.py
│   │   ├── user.py                   # Schema de utilizadores
│   │   ├── card.py                   # Schema de cartões
│   │   ├── transaction.py            # Schema de transações
│   │   └── merchant.py               # Schema de comerciantes
│   │
│   ├── routes/                       # Endpoints da API
│   │   ├── __init__.py
│   │   ├── auth.py                   # Login/registro
│   │   ├── users.py                  # Gestão de users
│   │   ├── cards.py                  # Gestão de cartões
│   │   ├── transactions.py           # Processar pagamentos
│   │   ├── liveness.py               # Verificação biométrica
│   │   └── locations.py              # Merchants e geolocalização
│   │
│   ├── services/                     # Lógica de negócio
│   │   ├── __init__.py
│   │   ├── risk_service.py           # Integra risk_engine
│   │   ├── liveness_service.py       # Integra liveness_detector_v2
│   │   ├── payment_service.py        # Orquestra pagamentos
│   │   └── location_service.py       # Validação de localização
│   │
│   └── database/                     # MongoDB connection
│       ├── __init__.py
│       ├── connection.py             # Motor connection
│       └── seed.py                   # Dados iniciais (users/merchants)
│
├── frontend/                         # Novo frontend interativo
│   ├── index.html                    # Página principal
│   ├── css/
│   │   └── style.css                 # Estilos
│   ├── js/
│   │   ├── app.js                    # Lógica principal
│   │   ├── map.js                    # Integração mapa (Leaflet/Mapbox)
│   │   ├── api.js                    # Chamadas ao backend
│   │   └── liveness.js               # Captura webcam
│   └── assets/
│       └── images/
│
├── src/                              # Core mantido (renomear para lib/)
│   └── core/
│       ├── liveness_detector_v2.py   # ✅ MANTIDO
│       ├── risk_engine.py            # ✅ MANTIDO
│       └── passive_liveness.py       # ✅ MANTIDO
│
├── data/                             # Dados de seed
│   ├── merchants.json                # Lojas/restaurantes com coordenadas
│   └── sample_users.json             # Utilizadores de teste
│
├── requirements.txt                  # Atualizar com: pymongo, fastapi, etc
├── .env.example                      # Template de variáveis ambiente
├── docker-compose.yml                # MongoDB + Backend + Frontend
└── README.md                         # Nova documentação
```

---

## 📦 Próximos Passos (Ordem)

### Passo 1: Configurar MongoDB ✅
```bash
# Instalar MongoDB localmente ou usar Docker
docker run -d -p 27017:27017 --name biotrust-mongo mongo:latest

# Instalar dependências Python
pip install pymongo motor fastapi uvicorn pydantic-settings
```

### Passo 2: Criar Schemas MongoDB
- `models/user.py` - ID, nome, email, cartões, histórico de localização
- `models/card.py` - Número (encriptado), validade, CVV hash
- `models/transaction.py` - Montante, merchant, localização, timestamp, resultado liveness
- `models/merchant.py` - Nome, coordenadas (lat/lng), categoria, descrição

### Passo 3: Backend FastAPI Básico
- API REST para CRUD de users/cards
- Endpoint `/api/transactions/process` - Processar pagamento
- Endpoint `/api/liveness/verify` - Verificação biométrica
- Endpoint `/api/locations/nearby` - Merchants próximos

### Passo 4: Frontend com Mapa
- Mapa interativo (Leaflet.js ou Mapbox)
- Selecionar localização do utilizador
- Ver merchants próximos
- Clicar num merchant para fazer compra

### Passo 5: Fluxo de Pagamento
1. User escolhe localização no mapa
2. Ve merchants próximos
3. Clica num merchant
4. Escolhe produto/valor
5. Sistema analisa risco (localização, valor, histórico)
6. Se alto risco → Ativa liveness detection
7. Webcam abre, challenges aparecem
8. Sistema valida e aprova/rejeita

---

## 🎯 Decisões de Arquitetura

### Banco de Dados: MongoDB
- Schema flexível para merchas e transações
- Bom para dados geoespaciais (coordenadas)
- Queries por localização ($near, $geoWithin)

### Backend: FastAPI
- Rápido, moderno, async
- Auto-documentação (Swagger)
- Fácil integração com OpenCV/MediaPipe

### Frontend: HTML + Vanilla JS + Leaflet
- Simples, sem frameworks pesados
- Leaflet.js para mapas (open-source)
- Fetch API para comunicar com backend

### Mapa: OpenStreetMap + Leaflet.js
- Gratuito, sem API keys
- Markers customizáveis para merchants
- Click events para interação

---

## 🚀 Começar Agora

**Execute o script de limpeza:**
```cmd
cleanup.bat
```

**Depois confirma:**
- Queres MongoDB local ou Docker?
- Região do mapa para carregar (Lisboa? Porto? Portugal inteiro?)
- Tipos de merchants (restaurantes, lojas, farmácias?)