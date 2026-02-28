# 🧪 GUIA DE TESTE - BioTrust

## ✅ Checklist de Testes

### 1. Testar API (Backend)

**Terminal 1:**
```bash
.\venv310\Scripts\python.exe api_server.py
```

**Verificações:**
- [ ] API inicia sem erros
- [ ] Mensagem "Starting BioTrust API Server..." aparece
- [ ] Acesso http://localhost:8000/docs funciona
- [ ] Acesso http://localhost:8000/health retorna status "healthy"

**Testar no Swagger (http://localhost:8000/docs):**

**Teste 1: Risk Analysis**
- [ ] POST /api/analyze-risk
- [ ] Click "Try it out"
- [ ] Click "Execute" com valores padrão
- [ ] Resultado mostra risk_score, risk_level, requires_liveness

**Teste 2: Liveness Verification** ⚠️ (REQUER CÂMERA)
- [ ] POST /api/verify-liveness
- [ ] Parâmetros: mode=active, enable_passive=true
- [ ] Siga instruções: piscar 3x, virar cabeça
- [ ] Resultado mostra verified=true, heart_rate detectado

**Teste 3: Payment Processing** ⚠️ (REQUER CÂMERA)
- [ ] POST /api/process-payment
- [ ] Use valores padrão
- [ ] Complete liveness check
- [ ] Resultado mostra status=APPROVED, transaction_id gerado

---

### 2. Testar Frontend Streamlit

**Terminal 2 (manter API rodando no Terminal 1):**
```bash
.\venv310\Scripts\streamlit run web_app.py
```

**Acesse:** http://localhost:8501

**Página HOME:**
- [ ] Métricas aparecem (3 Risk Levels, 3 Liveness Modes)
- [ ] Status da API mostra "✅ API Server: Online"
- [ ] Features cards aparecem corretamente

**Página RISK ANALYSIS:**
- [ ] Formulário carrega
- [ ] Preencher dados e clicar "🔍 Analyze Risk"
- [ ] Resultado mostra Risk Score, Risk Level, Liveness Required
- [ ] Breakdown de fatores aparece

**Página LIVENESS CHECK:** ⚠️ (REQUER CÂMERA)
- [ ] Selecionar mode: Active
- [ ] Marcar "Enable rPPG (Heart Rate)"
- [ ] Clicar "📸 Start Verification"
- [ ] Seguir instruções na webcam
- [ ] Resultado mostra heart rate e confidence

**Página PAYMENT PROCESSING:** ⚠️ (REQUER CÂMERA)
- [ ] Preencher dados de pagamento
- [ ] Selecionar liveness_mode: active
- [ ] Clicar "💰 Process Payment"
- [ ] Ver progress bar (3 etapas)
- [ ] Resultado: APPROVED com balões 🎈
- [ ] Transaction ID aparece

**Página TRANSACTION HISTORY:**
- [ ] Transações anteriores aparecem
- [ ] Estatísticas calculadas (Approved, Rejected, Avg Risk)
- [ ] Expandir transação mostra detalhes
- [ ] Botão "Clear History" funciona

---

### 3. Testar Frontend HTML

**Abrir arquivo:**
```
index.html (duplo clique ou arrastar para navegador)
```

**API deve estar rodando!**

**Verificações:**
- [ ] Status API mostra "API Online" (bolinha verde piscando)
- [ ] Tabs funcionam (Home, Risk Analysis, Liveness, Payment)
- [ ] Tab HOME: métricas aparecem com gradientes
- [ ] Tab RISK: formulário envia e mostra resultado verde/vermelho
- [ ] Tab LIVENESS: ⚠️ funciona com câmera do servidor
- [ ] Tab PAYMENT: ⚠️ processa pagamento completo

---

### 4. Testar Sistema Console (Legado)

**Teste Integrado:**
```bash
.\venv310\Scripts\python.exe test_integrated_liveness.py
```
- [ ] Câmera abre
- [ ] Piscar 3 vezes detectado
- [ ] Virar cabeça esquerda/direita detectado
- [ ] Heart rate calculado (ex: 51 BPM)
- [ ] Resultado: APPROVED (Active + Passive pass)

**Demo Completo:**
```bash
.\venv310\Scripts\python.exe demo_liveness.py
```
- [ ] Menu aparece com 4 opções
- [ ] Opção 1 (Active): funciona
- [ ] Opção 2 (Passive): detecta heart rate em 15s
- [ ] Opção 3 (Multi): faz ambos sequencialmente
- [ ] Opção 4 (Standalone Passive): teste de 15s funciona

**Payment System:**
```bash
.\venv310\Scripts\python.exe main_app.py
```
- [ ] Menu principal aparece
- [ ] Opção 1: cenário low-risk aprova rápido
- [ ] Opção 2: cenário high-risk pede liveness
- [ ] Opção 3: simulação automática funciona
- [ ] Opção 4: estatísticas aparecem

---

## 🐛 Problemas Comuns

**"Port 8000 already in use"**
```bash
# Encontrar processo
netstat -ano | findstr :8000
# Matar processo
taskkill /PID <número> /F
```

**"API Offline" no frontend**
- Certifique-se que api_server.py está rodando
- Acesse http://localhost:8000/health no navegador
- Verifique firewall do Windows

**"Camera not found"**
- Verifique permissões da câmera no Windows
- Teste com liveness_detector.py standalone
- Outros programas podem estar usando a câmera

**Streamlit não abre automaticamente**
- Abra manualmente: http://localhost:8501
- Certifique-se que não há outro Streamlit rodando

---

## 📊 Teste Rápido (5 minutos)

1. **Iniciar tudo:**
   ```bash
   .\start_all.bat
   ```

2. **Streamlit abre automaticamente:**
   - Ir para página "Payment Processing"
   - Valor: 2500 MZN
   - Click "Process Payment"
   - Fazer liveness test
   - Ver resultado APPROVED

3. **Verificar Swagger:**
   - Abrir http://localhost:8000/docs
   - Testar POST /api/analyze-risk
   - Ver resposta JSON

4. **Abrir HTML:**
   - Duplo click em index.html
   - Tab "Risk Analysis"
   - Enviar formulário
   - Ver resultado

**PRONTO! Sistema completo testado! ✅**

---

## 🎯 Demo para Juízes (TecStorm '26)

**Sequência recomendada:**

1. **Mostrar Swagger API** (1 min)
   - http://localhost:8000/docs
   - Mostrar documentação automática
   - Executar POST /api/analyze-risk

2. **Streamlit - Risk Analysis** (1 min)
   - Página Risk Analysis
   - Mostrar 3 cenários: low, medium, high risk

3. **Streamlit - Payment + Liveness** (2 min)
   - Página Payment Processing
   - Fazer pagamento com active + passive
   - Mostrar heart rate sendo detectado
   - APPROVED com transaction ID

4. **Console - Passive Liveness** (1 min)
   - Executar demo_liveness.py
   - Opção 2: Standalone Passive
   - Mostrar FFT graph (se implementado)
   - Explicar rPPG como diferenciador

**Total: 5 minutos de demo impactante! 🚀**
