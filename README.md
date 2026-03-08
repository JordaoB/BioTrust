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
  - 50% baseado no valor da transação
  - 45% baseado na distância geográfica
  - Amplificadores para cenários extremos
- 🚦 **Decisões automáticas**:
  - Baixo risco (< 40) → Aprovação imediata
  - Alto risco (≥ 40) → Requer liveness
- 🌍 **Análise geográfica**:
  - Lisboa (casa) → risco baixo
  - Porto (~300km) → risco médio
  - Faro (~500km) → risco alto

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
│  │  ├─ Análise de valor (50% do score)                │  │
│  │  ├─ Análise geográfica (45% do score)              │  │
│  │  ├─ Perfil comportamental                           │  │
│  │  ├─ Score final 0-100                               │  │
│  │  └─ Decisão: < 40 = Aprovação | ≥ 40 = Liveness   │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │ (se risco ≥ 40)                              │
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

### Computer Vision & AI
- **OpenCV** - Processamento de imagem e vídeo
- **MediaPipe** - Face mesh detection (468 landmarks)
- **NumPy + SciPy** - Processamento numérico avançado

### Frontend
- **HTML5 + CSS3 + JavaScript**
- **TailwindCSS** - Framework CSS utility-first
- **Font Awesome** - Icons
- **Vanilla JS** - Sem frameworks pesados

### DevOps
- **Docker** - Containerização
- **Uvicorn** - ASGI server
- **Git** - Controlo de versão

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

---

## 🎯 Demo

### Cenário 1: Transação de Baixo Risco ✅

```
Ação: Enviar €100 para João Silva (Lisboa - mesma cidade)
Risco: ~25 pontos (baixo)
Resultado: ✅ Aprovação IMEDIATA (sem liveness)
Saldo: Deduzido automaticamente
```

### Cenário 2: Transação de Médio Risco ⚠️

```
Ação: Enviar €1.000 para Maria Santos (Porto - 300km)
Risco: ~55 pontos (médio)
Resultado: 🔐 LIVENESS REQUERIDO → Janela OpenCV abre
Desafios: 4 desafios aleatórios
```

### Cenário 3: Transação de Alto Risco 🚨

```
Ação: Enviar €5.000 para Sofia (Faro - 500km+)
Risco: ~95 pontos (crítico)
Resultado: 🔐 LIVENESS OBRIGATÓRIO → 5 desafios
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
- ✅ Risk scoring contextual (50% valor + 45% distância)
- ✅ Liveness detection com 5 desafios
- ✅ Sistema de erros inteligente (reset/block)
- ✅ Interface MBWay-style completa
- ✅ Gestão de contactos e transações
- ✅ Histórico detalhado com filtros
- ✅ Autenticação por sessão (24h)
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

## 🐛 Troubleshooting

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
