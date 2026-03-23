<div align="center">

# 🔐 BioTrust

### *"Deepfakes não têm pulsação"*

**Sistema de Pagamentos com Autenticação Biométrica e Deteção de Liveness**

[![TecStorm '26](https://img.shields.io/badge/TecStorm-'26-blueviolet?style=for-the-badge&logo=trophy)](https://tecstorm.pt)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-8.2-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)

---

### 🏆 TecStorm '26 - Payments Without Limits

**Sistema completo de pagamentos estilo MBWay com segurança biométrica avançada**

</div>

---

## 📖 O que é o BioTrust?

**BioTrust** é uma **plataforma completa de pagamentos** que combina:

- 💳 **Sistema de Carteira Real** - Gestão de cartões com saldos, limites e validações
- 🔐 **Autenticação Biométrica** - Liveness detection com desafios aleatórios
- 🧠 **Risk Engine Inteligente** - Decisões contextuais baseadas em risco
- 💸 **Transações Completas** - Sistema de transferências com validação de saldo
- 🎨 **Interface MBWay-style** - Dashboard moderno com design português

---

## ✨ Features

### 💳 Sistema de Carteira & Pagamentos

✅ **Gestão de Cartões**
- Adicionar múltiplos cartões (Visa, Mastercard, Amex)
- Validação Luhn algorithm (rejeita números inválidos)
- Saldo individual por cartão
- Limites diários e por transação
- Definir cartão principal

✅ **Transações Reais**
- ✅ Validação de saldo antes da transação
- ✅ Verificação de limite diário (reset automático)
- ✅ Limite máximo por transação
- ✅ Dedução automática do saldo após aprovação
- ✅ Histórico completo de transações

✅ **Sistema de Contactos**
- Lista automática de utilizadores registados
- Enviar dinheiro para qualquer contacto
- Histórico de transações bilateral

### 🔐 Autenticação & Segurança

✅ **Liveness Detection V3**
- 🎲 **5 tipos de desafios aleatórios**:
  - Piscar os olhos 3 vezes
  - Sorrir
  - Virar cabeça à esquerda
  - Virar cabeça à direita  
  - Levantar sobrancelhas
- 🔄 **Sequência aleatória** (3-5 desafios)
- ⚠️ **Sistema de erros inteligente**:
  - 1º erro → Reset para início
  - 2º erro → Transação bloqueada
- 🎯 **Thresholds otimizados** para deteção precisa

✅ **Risk Engine**
- 📊 **Cálculo de risco** (0-100 pontos):
  - 30% localização/distância (inclui Impossible Travel)
  - 25% montante (absoluto + comparação histórica)
  - 20% velocity/frequência (janelas 1h/2h)
  - 15% confiança do destinatário/comerciante
  - 10% horário (noite/madrugada)
- 🚦 **Decisões automáticas**:
  - 0-25 → Aprovação imediata
  - 26-59 → Requer liveness
  - 60-100 → Alto risco (liveness obrigatório)
- 🌍 **Análise geográfica**:
  - Impossible Travel: >100km em <30 min = risco máximo de localização
  - País diferente e distância elevada aumentam score fortemente
  - Histórico de localização influencia a decisão

✅ **Machine Learning - Anomaly Detection**
- 🤖 **Isolation Forest** para detetar padrões anómalos
- 📊 **10 features engenheiradas**:
  - Valor da transação (normalizado)
  - Hora do dia e dia da semana
  - Distância de casa
  - Velocidade de transações (última hora)
  - Frequência diária
  - Ratio de valor vs média do utilizador
  - Timing suspeito (noite, fim-de-semana)
- 🎯 **Detecção em tempo real** (<100ms)
- 📝 **Explicações legíveis**: "Valor elevado: €5,000 (típico: €50)"
- 🔄 **Ajuste automático de risco**: Score de anomalia incrementa risco base
- 💾 **Model persistence**: Treino offline, predição online
- 📈 **Retraining**: Script automático para atualizar o modelo

### 🎨 Interface Web

✅ **Dashboard Moderno**
- 💰 Saldo total (soma de todos os cartões)
- 💳 Visualização de cartões com saldo individual
- 🎯 Enviar dinheiro com modal estilo MBWay
- 📊 Histórico de transações recente
- ✅ Notificações toast elegantes

✅ **Gestão de Cartões**
- Adicionar novos cartões
- Ver saldo disponível em cada cartão
- Limite diário e gasto hoje
- Layout com gradientes por tipo de cartão

✅ **Perfil do Utilizador**
- Dados pessoais
- Estatísticas de conta
- Logout seguro

### 📊 Logging & Auditoria

✅ **Sistema de Logs Completo** (loguru)
- 📝 **6 tipos de logs separados**:
  - Console: Colorido com emojis em tempo real
  - General: Logs gerais do sistema (30 dias)
  - Errors: Apenas erros (90 dias)
  - Audit Trail: Transações com contexto completo (365 dias, JSON)
  - Liveness: Tentativas de verificação biométrica (60 dias)
  - Security: Eventos de autenticação (180 dias)
- 🔄 **Rotação automática**: Daily midnight rotation
- 🗜️ **Compressão**: ZIP automático de logs antigos
- 🔍 **Rastreabilidade**:
  - IP address e User-Agent em todos os eventos
  - transaction_id para tracking completo
  - Timestamps UTC em formato ISO
- 📊 **Audit Trail estruturado**:
  - Todas as decisões de transação
  - Montantes, status, risk score, anomaly score
  - Liveness verificado (sim/não)
  - Razões de aprovação/rejeição

✅ **Observabilidade Operacional**
- 📈 **Métricas runtime** em `/api/observability/metrics`:
  - Taxa de aprovação/rejeição de transações
  - Taxa de falha de liveness
  - Tempo médio por etapa (transação, liveness, settlement)
- 🚨 **Alertas runtime** em `/api/observability/alerts`:
  - Pico de rejeições
  - Pico de falhas de liveness
  - Falhas de settlement
  - Erros de base de dados

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                  🌐 FRONTEND WEB                            │
│         Dashboard HTML/CSS/JS + TailwindCSS                 │
│    (Login, Cartões, Transações, Perfil, Histórico)         │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (FastAPI)
┌──────────────────────▼──────────────────────────────────────┐
│                  ⚙️ BACKEND (FastAPI + MongoDB)             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  💳 Sistema de Carteira                             │  │
│  │  ├─ Gestão de cartões com saldo                     │  │
│  │  ├─ Validação Luhn algorithm                        │  │
│  │  ├─ Limites diários e por transação                 │  │
│  │  └─ Dedução automática de saldo                     │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐  │
│  │  🧠 Risk Engine (Motor de Risco)                   │  │
│  │  ├─ Localização/Distância (30%)                    │  │
│  │  ├─ Montante (25%) + Velocity (20%)                │  │
│  │  ├─ Destinatário (15%) + Horário (10%)             │  │
│  │  ├─ Score final 0-100                               │  │
│  │  └─ Decisão: <=25 aprova | >25 liveness            │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐  │
│  │  🤖 ML Anomaly Detector (Isolation Forest)         │  │
│  │  ├─ 10 features: amount, time, distance, velocity  │  │
│  │  ├─ Anomaly score: 0-100                            │  │
│  │  ├─ Explicação: "High amount", "Unusual distance"  │  │
│  │  ├─ Risk boost: +15% max                            │  │
│  │  └─ Model: models/anomaly_detector.pkl              │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │ (se risco > 25)                              │
│  ┌────────────▼─────────────────────────────────────────┐  │
│  │  🔐 Liveness Detection V3                          │  │
│  │  ├─ 5 desafios aleatórios:                          │  │
│  │  │  • Piscar 3 vezes                                │  │
│  │  │  • Sorrir                                        │  │
│  │  │  • Virar cabeça esquerda                         │  │
│  │  │  • Virar cabeça direita                          │  │
│  │  │  • Levantar sobrancelhas                         │  │
│  │  ├─ MediaPipe Face Mesh (468 landmarks)            │  │
│  │  ├─ Sistema de erros inteligente                    │  │
│  │  └─ OpenCV para processamento                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  📊 Logging System (loguru) - 6 log types                   │
│  💾 MongoDB: users, cards, transactions, merchants          │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack

### Backend
- **Python 3.10+**
- **FastAPI 2.0** - Framework web moderno e rápido
- **MongoDB 8.2** - Database NoSQL para flexibilidade
- **Motor/PyMongo** - Driver async para MongoDB
- **loguru** - Logging estruturado com rotação e compressão

### Computer Vision & AI
- **OpenCV** - Processamento de imagem e vídeo
- **MediaPipe** - Face mesh detection (468 landmarks)
- **NumPy + SciPy** - Processamento numérico avançado
- **scikit-learn** - Machine Learning (Isolation Forest para anomaly detection)
- **joblib** - Model persistence e serialização

### Frontend
- **HTML5 + CSS3 + JavaScript**
- **TailwindCSS** - Framework CSS utility-first
- **Font Awesome** - Icons
- **Vanilla JS** - Sem frameworks pesados

### DevOps
- **Docker** - Containerização
- **Uvicorn** - ASGI server
- **Git** - Controlo de versão

### CI/CD
- **GitHub Actions** - Pipeline em `.github/workflows/ci.yml`
  - Lint crítico (`ruff`)
  - Testes automáticos E2E (`pytest`)
  - Build Docker (`docker build`)

---

## 🚀 Quick Start

### 1️⃣ Clone o Repositório

```bash
git clone https://github.com/your-username/biotrust.git
cd biotrust
```

### 2️⃣ Instalar Dependências

```bash
# Criar virtual environment
python -m venv venv310

# Ativar (Windows)
venv310\Scripts\activate

# Instalar packages
pip install -r requirements.txt
```

### 3️⃣ Iniciar MongoDB

```bash
# Opção 1: Script automático (Windows)
start_mongodb_local.bat

# Opção 2: Manual
mongod --dbpath mongodb_data
```

### 4️⃣ Popular Database (Opcional)

```bash
# Seed com 5 utilizadores + merchants
python data/seed_database.py
```

**Utilizadores de teste** (password: `password123`):
- `joao.silva@example.com` - €2.500 (Lisboa)
- `maria.santos@example.com` - €800 (Porto)
- `ana.costa@example.com` - €5.000 + €3.000 (Braga, 2 cartões)
- `pedro.oliveira@example.com` - €1.500 (Lisboa)
- `sofia.rodrigues@example.com` - €1.200 (Porto)

### 4.5️⃣ Treinar Modelo de ML (Anomaly Detection)

```bash
# Treina o modelo Isolation Forest com transações históricas
python data/train_anomaly_model.py
```

**Nota:** Necessário ter pelo menos 10 transações na database. Executar após `seed_database.py`.

### 5️⃣ Iniciar Backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API disponível em: **http://localhost:8000**

### 6️⃣ Abrir Interface Web

```bash
# Abrir browser automaticamente
open_web.bat

# Ou manualmente:
# http://localhost:8000/static/login.html
```

### 7️⃣ Publicar com Link (GitHub + Render)

Para abrir no telemóvel fora da tua rede local, publica o backend+frontend com URL pública.

1. Fazer push do projeto para GitHub.
2. Criar conta em Render e selecionar **New Web Service**.
3. Ligar ao repositório GitHub.
4. Configurar:
- Runtime: **Docker**
- Branch: `main`
- Health check: `/api/observability/metrics`
5. Definir variáveis de ambiente (produção):
- `MONGODB_URI` (preferencialmente MongoDB Atlas)
- `SECRET_KEY`
- `ENCRYPTION_KEY`
- `CORS_ORIGINS` com o domínio público do Render
6. Deploy e abrir o URL gerado (`https://...onrender.com`) no telemóvel.

**Nota:** O frontend já serve em `/static`, por isso basta um único serviço para ter login/dashboard acessível por link.

---

## 🎯 Demo

### Cenário 1: Transação de Baixo Risco ✅

```
Ação: Enviar €100 para João Silva (Lisboa - mesma cidade)
Risco: <=25 pontos (baixo)
Resultado: ✅ Aprovação IMEDIATA (sem liveness)
Saldo: Deduzido automaticamente
```

### Cenário 2: Transação de Médio Risco ⚠️

```
Ação: Enviar €1.000 para Maria Santos (Porto - 300km)
Risco: 26-59 pontos (médio)
Resultado: 🔐 LIVENESS REQUERIDO → Janela OpenCV abre
Desafios: sequência aleatória (3-5)
```

### Cenário 3: Transação de Alto Risco 🚨

```
Ação: Enviar €5.000 para Sofia (Faro - 500km+)
Risco: >=60 pontos (alto)
Resultado: 🔐 LIVENESS OBRIGATÓRIO
Dificuldade: Máxima, erros voltam ao início
```

### Como Testar Liveness

1. **Janela OpenCV abre**: Verde com câmara ativa
2. **Desafio aparece**: Ex: "Turn head LEFT"
3. **Executar ação**: Virar cabeça para a esquerda
4. **Feedback visual**: Verde ✅ quando detetado
5. **Próximo desafio**: Sequência até finalizar
6. **Resultado**:
   - ✅ Todos corretos → Transação aprovada, saldo deduzido
   - ❌ 1 erro → Reset para desafio 1
   - ❌ 2 erros → Transação BLOQUEADA

---

## 📡 API

### Endpoints Principais

#### Autenticação
```http
POST /api/auth/register    # Criar conta
POST /api/auth/login        # Login
GET  /api/auth/session/{token}  # Verificar sessão
POST /api/auth/logout       # Logout
```

#### Utilizadores
```http
GET    /api/users/{user_id}
GET    /api/users/{user_id}/cards
GET    /api/users/{user_id}/contacts
GET    /api/users/{user_id}/transactions
POST   /api/users/{user_id}/cards
DELETE /api/users/{user_id}/cards/{card_id}
```

#### Transações
```http
POST  /api/transactions/
GET   /api/transactions/{transaction_id}
GET   /api/transactions/user/{user_id}
PATCH /api/transactions/{transaction_id}/liveness
```

#### Liveness
```http
POST /api/liveness/verify
```

### Exemplo de Transação

```javascript
const response = await fetch('http://localhost:8000/api/transactions/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: "69adb7467976aaddb7f6e52c",
    amount: 1000.0,
    type: "transfer",
    recipient_email: "joao.silva@example.com",
    user_location: {
      city: "Porto",
      lat: 41.1579,
      lon: -8.6291
    }
  })
});

const transaction = await response.json();
// {
//   _id: "...",
//   risk_score: 55,
//   liveness_required: true,
//   status: "pending"
// }
```

---

## 🌍 Estrutura do Projeto

```
BioTrust/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configurações
│   ├── database/            # MongoDB connection
│   ├── models/              # Pydantic models
│   │   ├── user.py
│   │   ├── card.py
│   │   ├── transaction.py
│   │   └── merchant.py
│   └── routes/              # API endpoints
│       ├── auth.py
│       ├── users.py
│       ├── cards.py
│       ├── transactions.py
│       ├── merchants.py
│       └── liveness.py
├── src/core/
│   ├── liveness_detector_v3.py  # Sistema biométrico
│   └── risk_engine.py           # Motor de risco
├── web/
│   ├── login.html           # Página de login
│   ├── dashboard.html       # Dashboard principal
│   ├── cards.html           # Gestão de cartões
│   ├── transaction-history.html
│   ├── profile.html
│   └── js/
│       ├── dashboard.js
│       ├── cards.js
│       └── auth.js
├── data/
│   ├── seed_database.py     # Popular BD
│   ├── seed_users.json
│   └── seed_merchants.json
├── tests/
│   ├── test_integrated_liveness.py
│   └── test_system.py
└── requirements.txt
```

---

## 📊 Cartões de Teste Válidos

Use estes números com validação Luhn:

```
Visa:       4532015112830366
            4916338506082832
            4024007134564842

Mastercard: 5425233430109903
            2221000010000015

Amex:       374245455400126
```

---

## 📝 Funcionalidades do Sistema

### ✅ Já Implementado

- ✅ Sistema de carteira com saldos reais
- ✅ Validações de limite diário e por transação
- ✅ Dedução automática de saldo
- ✅ Verificação Luhn para números de cartão
- ✅ Risk engine multi-fator (30/25/20/15/10)
- ✅ Liveness detection com 5 desafios
- ✅ Sistema de erros inteligente (reset/block)
- ✅ Interface MBWay-style completa
- ✅ Gestão de contactos e transações
- ✅ Histórico detalhado com filtros
- ✅ Sessões com access token + refresh token
- ✅ MongoDB com schemas flexíveis
- ✅ Docker support

### 🔮 Melhorias Futuras

- [ ] Sessões em Redis (atualmente in-memory)
- [ ] Tokenização de cartões
- [ ] Rate limiting nos endpoints
- [ ] Audit logging completo
- [ ] Notificações push
- [ ] 2FA adicional
- [ ] Modo escuro
- [ ] App mobile nativa

---

## 🔒 Checklist de Produção

Antes de deploy em produção, validar:

1. **Secrets management**
- Não usar secrets hardcoded.
- Configurar `SECRET_KEY` e `ENCRYPTION_KEY` via secrets manager (AWS Secrets Manager / Azure Key Vault / GCP Secret Manager).

2. **CORS e Hosts restritos**
- Definir `CORS_ORIGINS` apenas para domínios frontend oficiais.
- Definir `ALLOWED_HOSTS` para domínios/API gateway reais.

3. **Headers de segurança e rate limit**
- Manter `SECURITY_HEADERS_ENABLED=True`.
- Manter `RATE_LIMIT_ENABLED=True` e ajustar `RATE_LIMIT_REQUESTS_PER_MINUTE`.

4. **Política de logs sensíveis**
- Rever retention por tipo de log (30/60/90/180/365 dias).
- Garantir que dados sensíveis não são logados (tokens, dados completos de cartão, biometria bruta).

5. **Observabilidade e alertas**
- Integrar `/api/observability/metrics` em dashboard.
- Integrar `/api/observability/alerts` em sistema de alerta (Slack/Teams/PagerDuty).

6. **CI/CD obrigatório antes de deploy**
- Lint crítico.
- Testes automáticos (E2E mínimo).
- Build Docker válido.

7. **Hardening de container**
- `read_only` filesystem + `tmpfs`.
- `cap_drop: [ALL]` + `no-new-privileges`.

---

## � Documentação Completa

Para informações detalhadas sobre componentes específicos:

- **[Sistema de Logging](docs/LOGGING_SYSTEM.md)** - Logs estruturados, audit trail, retention policies
- **[ML Anomaly Detection](docs/ML_ANOMALY_DETECTION.md)** - Machine Learning para detetar fraudes, training, tuning
- **[Guia da API](docs/GUIA_API_WEB.md)** - Endpoints da API REST
- **[Passive Liveness](docs/PASSIVE_LIVENESS_TECH.md)** - Tecnologias de deteção biométrica
- **[Estrutura do Projeto](docs/PROJECT_STRUCTURE.md)** - Organização dos ficheiros

---

## �🐛 Troubleshooting

### MongoDB não inicia
```bash
# Criar pasta se não existir
mkdir mongodb_data

# Iniciar manualmente
mongod --dbpath mongodb_data
```

### Porta 8000 já em uso
```bash
# Verificar processo
netstat -ano | findstr :8000

# Matar processo (Windows)
taskkill /PID <PID> /F
```

### Webcam não funciona
- Verificar permissões do browser
- Testar com Chrome/Edge (melhor suporte)
- Garantir boa iluminação

---

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

---

<div align="center">

**Desenvolvido para TecStorm '26** 🏆

*Segurança biométrica de próxima geração para pagamentos*

[![GitHub](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github)](https://github.com/your-repo)

</div>
