# 🚀 BioTrust - API REST & Frontend Web - Guia Rápido

## ✅ O que foi implementado

### 1. **API REST com FastAPI** 🌐

**Arquivo:** `api_server.py`

**Endpoints:**
- `GET /` - Root endpoint com informação do serviço
- `GET /health` - Health check
- `POST /api/analyze-risk` - Análise de risco de transação
- `POST /api/verify-liveness` - Verificação de liveness (active/passive)
- `POST /api/process-payment` - Processamento completo de pagamento

**Funcionalidades:**
- ✅ FastAPI com Pydantic models para validação
- ✅ Documentação automática Swagger UI
- ✅ CORS configurado para permitir frontend
- ✅ Integração com Risk Engine e Liveness Detector
- ✅ Transaction Logger integrado
- ✅ Suporte para 3 modos de liveness: active, passive, multi

### 2. **Frontend Streamlit** 🎨

**Arquivo:** `web_app.py`

**Páginas:**
- 🏠 **Home** - Visão geral do sistema
- 📊 **Risk Analysis** - Análise de risco interativa
- 👤 **Liveness Check** - Verificação de liveness
- 💳 **Payment Processing** - Processamento completo
- 📜 **Transaction History** - Histórico com estatísticas

**Features:**
- ✅ Interface moderna e profissional
- ✅ Cards de métricas e estatísticas
- ✅ Status da API em tempo real
- ✅ Formulários interativos
- ✅ Visualização de resultados colorida
- ✅ Histórico de transações persistente na sessão

### 3. **Frontend HTML/CSS/JS** 💻

**Arquivo:** `index.html`

**Features:**
- ✅ Interface standalone (sem dependências)
- ✅ Design gradiente moderno
- ✅ Status da API com indicador animado
- ✅ Tabs para diferentes funcionalidades
- ✅ Spinners de loading
- ✅ Resultados coloridos (sucesso/erro)
- ✅ Responsivo (mobile-friendly)

### 4. **Scripts de Inicialização** 🔧

**Arquivos criados:**
- `start_api.bat` - Inicia apenas a API
- `start_web.bat` - Inicia apenas o frontend Streamlit
- `start_html.bat` - Abre o frontend HTML
- `start_all.bat` - Inicia API + Streamlit automaticamente

---

## 📖 Como Usar

### Método 1: Sistema Completo (RECOMENDADO)

```bash
# Duplo clique ou execute no terminal:
start_all.bat
```

Isso vai:
1. Iniciar a API FastAPI em http://localhost:8000
2. Aguardar 5 segundos para API inicializar
3. Iniciar o Streamlit em http://localhost:8501
4. Abrir automaticamente no navegador

### Método 2: Componentes Individuais

**API Server:**
```bash
start_api.bat
# ou
.\venv310\Scripts\python.exe api_server.py
```

**Frontend Streamlit:**
```bash
start_web.bat
# ou
.\venv310\Scripts\streamlit run web_app.py
```

**Frontend HTML:**
```bash
start_html.bat
# ou
# Abrir index.html diretamente no navegador
```

---

## 🔗 URLs Importantes

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **API Docs** | http://localhost:8000/docs | Documentação Swagger interativa |
| **API ReDoc** | http://localhost:8000/redoc | Documentação alternativa |
| **API Health** | http://localhost:8000/health | Status da API |
| **Streamlit** | http://localhost:8501 | Interface web principal |
| **HTML** | `index.html` | Interface standalone |

---

## 🧪 Testando a API

### 1. Via Swagger UI (Browser)

Acesse http://localhost:8000/docs e teste diretamente:
- Clique em um endpoint
- Clique em "Try it out"
- Preencha os dados
- Clique em "Execute"

### 2. Via curl (Terminal)

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Risk Analysis:**
```bash
curl -X POST http://localhost:8000/api/analyze-risk \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 2500,
    "user_id": "user_123",
    "merchant_id": "merch_456",
    "location": "Maputo, Mozambique"
  }'
```

### 3. Via Python

```python
import requests

# Risk Analysis
response = requests.post(
    "http://localhost:8000/api/analyze-risk",
    json={
        "amount": 2500.00,
        "user_id": "user_123",
        "merchant_id": "merch_456",
        "location": "Maputo, Mozambique"
    }
)
print(response.json())
```

---

## 📊 Exemplo de Fluxo Completo

### Cenário: Pagamento de 2500 MZN

1. **Cliente acessa interface web** (Streamlit ou HTML)

2. **Preenche dados da transação:**
   - Valor: 2500 MZN
   - User ID: user_123
   - Merchant: Shop ABC
   - Localização: Maputo

3. **Sistema analisa risco automaticamente:**
   - Risk Score: 65/100
   - Risk Level: MEDIUM
   - Requires Liveness: ✅ YES

4. **Sistema solicita liveness check:**
   - Modo: Active + Passive (rPPG)
   - Usuário pisca 3 vezes
   - Usuário vira cabeça (esquerda/direita)
   - Sistema detecta batimento cardíaco: 72 BPM

5. **Pagamento aprovado:**
   - Transaction ID gerado
   - Log salvo
   - Confirmação enviada

---

## 🎯 Diferenciais Implementados

### 1. **API REST Profissional**
- Documentação automática (Swagger)
- Validação de dados (Pydantic)
- Error handling completo
- CORS configurado

### 2. **Dual Frontend**
- **Streamlit**: Rico e interativo (ideal para demos)
- **HTML/CSS/JS**: Leve e standalone (ideal para embeds)

### 3. **Integração Completa**
- Risk Engine + Liveness + Payment em 1 endpoint
- Modos de liveness configuráveis
- Transaction logging automático

### 4. **UX Profissional**
- Status indicators
- Loading spinners
- Resultados coloridos
- Responsive design

---

## 🐛 Troubleshooting

**API não inicia:**
```bash
# Verificar se porta 8000 está livre
netstat -ano | findstr :8000

# Matar processo se necessário
taskkill /PID <PID> /F
```

**Streamlit não conecta à API:**
- Verificar se API está rodando: http://localhost:8000/health
- Verificar firewall do Windows
- Verificar se CORS está habilitado no api_server.py

**Camera não funciona:**
- Verificar permissões de câmera no Windows
- Testar com liveness_detector.py standalone primeiro

---

## 📁 Arquivos do Sistema Web

```
BioTrust/
├── api_server.py          # FastAPI backend
├── web_app.py             # Streamlit frontend
├── index.html             # HTML/CSS/JS frontend
├── start_api.bat          # Script: API only
├── start_web.bat          # Script: Streamlit only
├── start_html.bat         # Script: HTML only
├── start_all.bat          # Script: Sistema completo
├── risk_engine.py         # Risk analysis module
├── liveness_detector.py   # Active liveness
├── passive_liveness.py    # Passive liveness (rPPG)
├── transaction_logger.py  # Transaction logging
└── requirements.txt       # Dependencies
```

---

## 🎓 Para os Juízes do TecStorm '26

### O que demonstrar:

1. **Swagger UI** (http://localhost:8000/docs)
   - Mostrar documentação automática
   - Executar um request ao vivo

2. **Interface Streamlit** (http://localhost:8501)
   - Navegar pelas páginas
   - Fazer análise de risco
   - Processar pagamento completo

3. **Passive Liveness (rPPG)**
   - Executar demo_liveness.py
   - Mostrar detecção de batimento cardíaco
   - Explicar o diferencial técnico

### Pontos fortes para destacar:

- ✅ **Sistema completo**: Backend + Frontend + API
- ✅ **Tecnologia avançada**: rPPG (heart rate via webcam)
- ✅ **Arquitetura profissional**: REST API + Multiple frontends
- ✅ **Pronto para produção**: Documentação, logging, error handling
- ✅ **Diferenciador**: Poucos times terão rPPG implementado

---

## 📈 Próximos Passos (Pós-Hackathon)

1. **WebRTC** - Streaming de vídeo cliente-servidor
2. **Database** - Persistência real (PostgreSQL)
3. **Authentication** - JWT tokens
4. **Rate Limiting** - Proteção contra abuse
5. **Monitoring** - Prometheus + Grafana
6. **Deploy** - Docker + AWS/Azure

---

**Desenvolvido com 💙 pela equipa BioTrust**

*TecStorm '26 - Payments Without Limits*
