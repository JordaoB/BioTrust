# Sistema de Logging e Audit Trail - BioTrust

## 📋 Visão Geral

Sistema completo de logging estruturado implementado com **loguru** para monitoramento, debugging e audit trail de todo o sistema BioTrust.

## ✅ O que foi implementado

### 1. **Módulo de Logging Centralizado** (`backend/utils/logger.py`)

Sistema de logging com múltiplos destinos e níveis de log:

#### **Logs de Console** (coloridos, tempo real)
- Formato legível para desenvolvimento
- Nível: INFO e superiores
- Coloração automática por nível de severidade

#### **Logs Gerais** (`logs/biotrust_*.log`)
- Rotação diária (meia-noite)
- Retenção: 30 dias
- Compressão: ZIP automática
- Nível: DEBUG e superiores

#### **Logs de Erro** (`logs/errors_*.log`)
- Apenas erros e exceções
- Retenção: 90 dias (logs críticos preservados por mais tempo)
- Rotação diária

#### **Audit Trail de Transações** (`logs/audit_transactions_*.log`)
- Formato JSON estruturado
- Retenção: 365 dias (conformidade)
- Regista: quem, quanto, quando, status, motivo
- Campos: user_id, amount, merchant_id, status, risk_score, liveness_verified, IP, User-Agent

#### **Logs de Liveness** (`logs/liveness_*.log`)
- Tentativas de verificação biométrica
- Detalhes de falhas (spoofing, timeout, etc.)
- Retenção: 60 dias
- Métricas: confidence, tempo de detecção, motivo da falha

#### **Logs de Segurança** (`logs/security_*.log`)
- Tentativas de login/logout
- Acessos não autorizados
- Tokens inválidos
- Retenção: 180 dias

---

## 🔍 Eventos Registados

### **Transações**
```python
✅ Transaction APPROVED (Low Risk)
⏳ Transaction PENDING (Liveness Required)
❌ Transaction REJECTED (Liveness Failed)
📝 Transaction created | User: xxx | Amount: €XX.XX
```

### **Liveness Detection**
```python
🚨 SPOOFING DETECTED | Texture: 0.15 | Screen replay
🚨 SPOOFING DETECTED | Moire: 0.45 | Screen filming
🚨 SPOOFING DETECTED | Color Variance: 30 | Compressed video
✅ Liveness PASSED | Challenges: 5/5 | HR: 72 BPM
❌ Liveness FAILED | rPPG confidence low
```

### **Autenticação**
```python
🔑 Registration attempt | Email: user@example.com | IP: 192.168.1.1
✅ User registered | ID: xxx | Email: xxx | Name: João Silva
⚠️ Registration failed | Email already exists
🔑 Login attempt | Email: xxx | IP: xxx
✅ Login successful | User: João Silva | IP: xxx
⚠️ Login failed | Invalid password | IP: xxx
🚪 Logout | User: xxx | Email: xxx
⚠️ Invalid access token attempt
```

---

## 📊 Funções Helper

### **log_transaction_audit()**
Regista audit trail completo de transações:
```python
log_transaction_audit(
    transaction_id="64abc123...",
    user_id="64def456...",
    amount=150.50,
    merchant_id="64ghi789...",
    status="APPROVED",
    risk_score=35.2,
    risk_level="LOW",
    liveness_verified=False,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    reason="Low risk - auto-approved"
)
```

### **log_liveness_attempt()**
Regista tentativas de verificação biométrica:
```python
log_liveness_attempt(
    user_id="64def456...",
    transaction_id="64abc123...",
    success=True,
    confidence=85.5,
    reason="All challenges passed",
    detection_time=12.3
)
```

### **log_security_event()**
Regista eventos de segurança:
```python
log_security_event(
    event_type="LOGIN_FAILED",
    user_id="user@example.com",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    details="Invalid password",
    severity="WARNING"
)
```

---

## 📁 Estrutura de Logs

```
logs/
├── biotrust_2026-03-09.log          # Logs gerais do dia
├── errors_2026-03-09.log            # Erros do dia
├── audit_transactions_2026-03-09.log # Audit trail transações
├── liveness_2026-03-09.log          # Verificações biométricas
├── security_2026-03-09.log          # Eventos de segurança
└── [arquivos comprimidos .zip]       # Logs antigos comprimidos
```

---

## 🔧 Integração nos Módulos

### **Rotas de Transações** (`backend/routes/transactions.py`)
- ✅ Log de criação de transação
- ✅ Log de aprovação automática (low risk)
- ✅ Log de transação pendente (liveness required)
- ✅ Log de atualização após liveness
- ✅ Log de erros com stack trace
- ✅ Audit trail completo com IP e User-Agent

### **Liveness Detector** (`src/core/liveness_detector_v3.py`)
- ✅ Log de detecção de spoofing (texture, moiré, color variance)
- ✅ Log de falha de rPPG
- ✅ Log de verificação bem-sucedida com métricas
- ✅ Log de erros e timeouts

### **Rotas de Autenticação** (`backend/routes/auth.py`)
- ✅ Log de tentativas de registro
- ✅ Log de registro bem-sucedido
- ✅ Log de falha de registro (email duplicado)
- ✅ Log de tentativas de login
- ✅ Log de login bem-sucedido
- ✅ Log de falha de login (credenciais inválidas)
- ✅ Log de logout
- ✅ Log de tokens inválidos/expirados
- ✅ Security events para auditoria

---

## 🎯 Benefícios

### **Debugging**
- Logs coloridos em tempo real no console
- Stack traces completas em erros
- Contexto completo de cada operação

### **Monitoramento**
- Múltiplos níveis de severidade
- Filtros por tipo de evento
- Timestamps precisos

### **Auditoria / Compliance**
- Registro permanente de transações (1 ano)
- Audit trail completo: quem, quando, quanto, porquê
- Logs de segurança (6 meses)
- Logs de liveness para análise anti-fraude

### **Análise**
- Formato JSON estruturado para parsing
- Fácil integração com ferramentas de análise
- Histórico de padrões de fraude
- Métricas de performance

### **Segurança**
- Detecção de tentativas de acesso não autorizado
- Logs de tokens inválidos
- Histórico de IPs e User-Agents
- Identificação de padrões suspeitos

---

## 🚀 Como Usar

### **Instalação**
```bash
pip install loguru==0.7.2
```

### **Importar o Logger**
```python
from backend.utils.logger import logger, log_transaction_audit, log_liveness_attempt, log_security_event
```

### **Exemplos de Uso**

**Log simples:**
```python
logger.info("Operação iniciada")
logger.success("Operação concluída com sucesso")
logger.warning("Aviso: comportamento suspeito")
logger.error("Erro ao processar pedido")
```

**Log com contexto:**
```python
logger.info(f"Usuário {user_id} realizou transação de €{amount:.2f}")
```

**Audit trail:**
```python
log_transaction_audit(
    transaction_id=tx_id,
    user_id=user_id,
    amount=amount,
    status="APPROVED",
    # ... outros campos
)
```

---

## 📈 Análise de Logs

### **Filtrar por tipo**
```bash
# Ver apenas transações
grep "TRANSACTION" logs/audit_transactions_*.log

# Ver apenas falhas de liveness
grep "FAILED" logs/liveness_*.log

# Ver tentativas de login falhadas
grep "LOGIN_FAILED" logs/security_*.log
```

### **Análise de padrões**
```python
# Exemplo: Contar transações aprovadas vs rejeitadas
import json
from collections import Counter

statuses = []
with open("logs/audit_transactions_2026-03-09.log") as f:
    for line in f:
        if "TRANSACTION" in line:
            # Parse do log
            parts = line.split("|")
            status = parts[4].strip()
            statuses.append(status)

print(Counter(statuses))
# Output: Counter({'APPROVED': 45, 'REJECTED': 3, 'PENDING': 2})
```

---

## 🔒 Retenção e Conformidade

| Tipo de Log | Retenção | Justificação |
|-------------|----------|--------------|
| Geral | 30 dias | Debugging recente |
| Erros | 90 dias | Análise de problemas |
| Transações | 365 dias | Conformidade legal |
| Liveness | 60 dias | Anti-fraude |
| Segurança | 180 dias | Auditoria de segurança |

**Compressão automática:** Todos os logs são comprimidos em ZIP após rotação para economizar espaço.

---

## 🎨 Emojis nos Logs

Para facilitar a leitura visual:
- ✅ Sucesso
- ❌ Falha
- ⏳ Pendente
- ⚠️ Aviso
- 🚨 Alerta crítico
- 🔑 Autenticação
- 🚪 Logout
- 📝 Criação
- 🔒 Liveness

---

## 🛠️ Manutenção

### **Limpeza manual de logs antigos**
```bash
# Apagar logs com mais de 1 ano
find logs/ -name "*.log.zip" -mtime +365 -delete
```

### **Monitorar tamanho dos logs**
```bash
du -sh logs/
```

### **Backup de logs críticos**
```bash
# Backup de audit trail
tar -czf audit_backup_$(date +%Y%m%d).tar.gz logs/audit_transactions_*.log
```

---

## 📝 Notas Importantes

1. **Performance:** O sistema de logging é assíncrono e não bloqueia operações
2. **Rotação:** Logs rodam automaticamente à meia-noite (UTC)
3. **Compressão:** Compressão ZIP economiza ~90% de espaço
4. **Thread-safe:** Loguru é thread-safe, múltiplos processos podem escrever simultaneamente
5. **Timestamps:** Todos os logs usam UTC para consistência

---

## 🔮 Próximas Melhorias (Opcional)

- [ ] Integração com ELK Stack (Elasticsearch, Logstash, Kibana)
- [ ] Alertas em tempo real via webhooks
- [ ] Dashboard de métricas em tempo real
- [ ] Exportação para Cloud Storage (S3, Azure Blob)
- [ ] Análise de ML para detecção de anomalias
- [ ] API REST para consulta de logs

---

**Sistema implementado por:** GitHub Copilot  
**Data:** Março 2026  
**Versão:** 1.0
