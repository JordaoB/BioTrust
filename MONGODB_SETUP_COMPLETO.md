# 📦 MongoDB Setup - Completo!

## ✅ O que foi criado:

### 1. **Modelos de Dados (Pydantic + MongoDB)**
```
backend/models/
├── user.py         - Utilizadores com localização e histórico
├── card.py         - Cartões encriptados (AES)
├── transaction.py  - Transações com risco + liveness
└── merchant.py     - Lojas com geolocalização
```

**Features:**
- `User`: Email único, password hash (bcrypt), localização home, histórico transações
- `Card`: Número encriptado (Fernet), CVV hash (SHA256), last 4 digits visíveis
- `Transaction`: Análise risco, resultado liveness, distâncias calculadas
- `Merchant`: Coordenadas GPS, categoria, horários de funcionamento

### 2. **Configuração e Database**
- `backend/config.py` - Settings com Pydantic Settings (lê .env)
- `backend/database/__init__.py` - Motor connection (MongoDB async)
- `.env.example` - Template atualizado com MongoDB configs

**Indexes criados:**
- Users: `email` (unique), `phone`
- Cards: `user_id`, `last_four`
- Transactions: `user_id`, `created_at`, composite
- **Merchants: `2dsphere` geospatial index** (queries por proximidade)

### 3. **Dados de Seed**
📍 **12 Merchants reais em Portugal:**
- **Lisboa** (5): Pastéis de Belém, Timeout Market, Farmácia Chiado, Pingo Doce, FNAC
- **Porto** (4): Café Majestic, Livraria Lello, Mercado Bolhão, Cafeína
- **Braga** (2): Bom Jesus Funicular, Centurium, Continente

👤 **5 Utilizadores de teste:**
- João Silva (Lisboa) - Conta antiga, baixo risco
- Maria Santos (Porto) - Conta nova, risco médio
- Ana Costa (Braga) - Premium, 2 cartões
- Pedro Oliveira (Lisboa)
- Sofia Rodrigues (Porto)

**Todos com password:** `password123`

### 4. **Scripts Automatizados**
- `setup_mongodb.bat` - Verifica MongoDB, instala deps, popula DB
- `data/seed_database.py` - Script Python que cria users/merchants/cards

---

## 🚀 Como Usar:

### **Opção 1: MongoDB Local**
```cmd
# Baixar e instalar MongoDB Community:
https://www.mongodb.com/try/download/community

# Executar setup:
setup_mongodb.bat
```

### **Opção 2: MongoDB via Docker**
```cmd
# Iniciar MongoDB container:
docker run -d -p 27017:27017 --name biotrust-mongo mongo:latest

# Popular dados:
python data\seed_database.py
```

---

## 📊 Verificar Dados:

```bash
# Conectar ao MongoDB
mongosh

# Usar database
use biotrust

# Ver utilizadores
db.users.find().pretty()

# Ver merchants
db.merchants.find().pretty()

# Ver cartões
db.cards.find().pretty()

# Query geoespacial (merchants perto de Lisboa centro)
db.merchants.find({
  "location.coordinates": {
    $near: {
      $geometry: { type: "Point", coordinates: [-9.1393, 38.7223] },
      $maxDistance: 5000
    }
  }
})
```

---

## 📁 Nova Estrutura do Projeto:

```
BioTrust/
├── backend/
│   ├── models/          ✅ User, Card, Transaction, Merchant
│   ├── database/        ✅ MongoDB connection + indexes
│   └── config.py        ✅ Settings (Pydantic)
│
├── data/
│   ├── seed_users.json      ✅ 5 utilizadores
│   ├── seed_merchants.json  ✅ 12 lojas reais
│   └── seed_database.py     ✅ Script de seeding
│
├── src/core/
│   ├── liveness_detector_v2.py  ✅ MANTIDO
│   ├── risk_engine.py           ✅ MANTIDO
│   └── passive_liveness.py      ✅ MANTIDO
│
├── .env.example         ✅ Atualizado com MongoDB
├── requirements.txt     ✅ Atualizado (motor, pymongo, etc)
├── setup_mongodb.bat    ✅ Setup automatizado
└── cleanup.bat          ✅ Limpar código antigo
```

---

## 🎯 Próximo Passo:

**Criar API Backend (FastAPI)**
- Endpoints REST para users, cards, transactions
- Integrar liveness_detector_v2.py no fluxo de pagamento
- Integrar risk_engine.py para análise de risco

Confirma que MongoDB está configurado e funcionando, depois avanço para o backend! 🚀
