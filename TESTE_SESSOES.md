# Sistema de Sessões Persistentes - Guia de Teste

## 🎯 O que foi implementado?

### Backend Changes
1. **Novo Modelo**: `backend/models/session.py`
   - Sessões armazenadas em MongoDB (não mais in-memory)
   - Access token (1 hora de validade)
   - Refresh token (30 dias de validade)
   - Metadata: IP, user agent, timestamps

2. **Auth Endpoints Atualizados**: `backend/routes/auth.py`
   - ✅ `POST /api/auth/register` - Retorna access + refresh tokens
   - ✅ `POST /api/auth/login` - Retorna access + refresh tokens
   - ✅ `POST /api/auth/logout` - Invalida sessão (marca como inactive)
   - ✅ `GET /api/auth/session/{access_token}` - Verifica token
   - ✅ `POST /api/auth/refresh` - Renova access token
   - ✅ `GET /api/auth/sessions/active` - Lista sessões ativas do utilizador
   - ✅ `DELETE /api/auth/sessions/{session_id}` - Revoga sessão específica
   - ✅ `DELETE /api/auth/sessions/cleanup` - Admin: limpa sessões expiradas

### Frontend Changes
3. **Token Manager**: `web/js/token-manager.js`
   - Gestão automática de tokens
   - Auto-refresh quando token expira em < 5 minutos
   - Retry automático em caso de 401
   - Logout centralizado

4. **Auth.js Atualizado**: `web/js/auth.js`
   - Login/Register salvam access_token + refresh_token
   - Auto-refresh ativo

5. **Dashboard.js Atualizado**: `web/js/dashboard.js`
   - Usa TokenManager para todos os pedidos
   - Logout via TokenManager

6. **Dashboard.html**: Inclui token-manager.js

### Database
7. **Script de Índices**: `data/create_session_indexes.py`
   - Índices únicos em access_token e refresh_token
   - Índice em user_id
   - TTL index para auto-cleanup de sessões expiradas

---

## 🧪 Como Testar

### 1. Setup Inicial

```bash
# Criar índices MongoDB (IMPORTANTE)
python data\create_session_indexes.py

# Reiniciar servidor FastAPI
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Testar Registro de Novo Utilizador

```bash
# Via Postman ou curl
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "phone": "912345678",
    "password": "password123"
  }'
```

**Resposta Esperada**:
```json
{
  "success": true,
  "message": "Account created successfully",
  "user": { ... },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access_token_expires_at": "2026-03-09T15:00:00",
  "refresh_token_expires_at": "2026-04-08T14:00:00"
}
```

### 3. Testar Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "joao.silva@example.com",
    "password": "password123"
  }'
```

**Resposta Esperada**: Igual ao register (tokens novos)

### 4. Testar Verificação de Sessão

```bash
# Substituir ACCESS_TOKEN pelo token recebido
curl http://localhost:8000/api/auth/session/ACCESS_TOKEN
```

**Resposta Esperada**:
```json
{
  "success": true,
  "user": {
    "_id": "...",
    "name": "João Silva",
    "email": "joao.silva@example.com",
    ...
  }
}
```

### 5. Testar Refresh Token

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "REFRESH_TOKEN_AQUI"
  }'
```

**Resposta Esperada**: Novo access_token (mesmo refresh_token)

### 6. Testar Auto-Refresh no Frontend

1. **Abrir dashboard**: http://localhost:8000/static/dashboard.html
2. **Login**: joao.silva@example.com / password123
3. **Abrir DevTools Console** (F12)
4. **Esperar 55 minutos** (ou ajustar tempo em token-manager.js para testar)
5. **Verificar console**: Deve aparecer "⏰ Auto-refresh triggered"

### 7. Testar Sessões Ativas

```bash
curl http://localhost:8000/api/auth/sessions/active?access_token=ACCESS_TOKEN
```

**Resposta Esperada**:
```json
{
  "success": true,
  "sessions": [
    {
      "_id": "...",
      "created_at": "2026-03-09T14:00:00",
      "last_activity": "2026-03-09T14:05:00",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0...",
      "is_current": true
    }
  ]
}
```

### 8. Testar Logout

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "ACCESS_TOKEN"
  }'
```

### 9. Testar Persistência (CRÍTICO)

1. **Login** no dashboard
2. **Verificar localStorage**: Deve ter `access_token`, `refresh_token`
3. **Reiniciar servidor** FastAPI (Ctrl+C e reiniciar)
4. **Recarregar dashboard** (F5)
5. **Resultado esperado**: Dashboard carrega normalmente (não redireciona para login)
6. **Antes** (in-memory): Redirecionava para login ❌
7. **Agora** (MongoDB): Mantém sessão ✅

---

## 🔍 Verificar MongoDB

```javascript
// No mongosh
use biotrust

// Ver sessões ativas
db.sessions.find({ is_active: true }).pretty()

// Ver sessões de um utilizador específico
db.sessions.find({ email: "joao.silva@example.com" }).pretty()

// Contar sessões
db.sessions.countDocuments()

// Ver índices criados
db.sessions.getIndexes()
```

---

## ❌ Erros Comuns

### 1. "Invalid or expired access token"
- **Causa**: Token expirou (> 1 hora)
- **Solução**: Usar refresh token ou fazer login novamente

### 2. "Refresh token expired"
- **Causa**: Refresh token expirou (> 30 dias)
- **Solução**: Fazer login novamente

### 3. "No access token available"
- **Causa**: localStorage vazio
- **Solução**: Fazer login

### 4. Índices não criados
- **Causa**: Script não executado
- **Solução**: `python data\create_session_indexes.py`

### 5. Frontend não encontra TokenManager
- **Causa**: Script não incluído no HTML
- **Solução**: Verificar se `<script src="/static/js/token-manager.js"></script>` está presente

---

## 📊 Benefícios

### Antes (In-Memory)
- ❌ Sessões perdem-se ao reiniciar servidor
- ❌ Não há histórico de sessões
- ❌ Token expira em 24h (sem renovação)
- ❌ Sem controlo de dispositivos
- ❌ Sem audit trail

### Agora (MongoDB + Refresh Tokens)
- ✅ Sessões persistem ao reiniciar
- ✅ Histórico completo (IP, user agent, timestamps)
- ✅ Access token renova automaticamente (1h)
- ✅ Refresh token válido por 30 dias
- ✅ Utilizador pode ver/revogar sessões
- ✅ Auto-cleanup de sessões expiradas (TTL index)
- ✅ Audit trail completo

---

## 🚀 Próximos Passos Sugeridos

1. **Rate Limiting**: Limitar tentativas de login/refresh
2. **Email Notifications**: Avisar quando nova sessão é criada
3. **Geolocalização**: Detetar logins suspeitos de locais diferentes
4. **Remember Me**: Checkbox para refresh token de 90 dias
5. **2FA**: Adicionar segundo fator de autenticação

---

## 📝 Notas de Segurança

- ✅ Tokens não armazenam dados sensíveis (apenas IDs)
- ✅ Sessões marcadas como inactive (não deletadas) para audit
- ✅ IP e User Agent registados para análise de segurança
- ✅ TTL index garante cleanup automático
- ⚠️ Tokens em localStorage (considerar httpOnly cookies para produção)
- ⚠️ HTTPS obrigatório em produção
