/* ==============================================
   BioTrust - API Communication Layer
   ==============================================
   
   Este ficheiro contém todas as funções para comunicar
   com o backend FastAPI.
   
   BASE_URL: http://localhost:8000
   
   Funções disponíveis:
   - getUsers()            → GET /api/users/
   - getUserByEmail()      → GET /api/users/email/{email}
   - getUserCards()        → GET /api/users/{id}/cards
   - createTransaction()   → POST /api/transactions/
   - getTransaction()      → GET /api/transactions/{id}
   - getLivenessRequirements() → GET /api/liveness/requirements/{tx_id}
   - simulateLiveness()    → POST /api/liveness/simulate
   - updateTransactionLiveness() → PATCH /api/transactions/{id}/liveness
   
   ============================================== */

// Configuração da API
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    TIMEOUT: 10000, // 10 segundos
};

/* ==============================================
   HELPER FUNCTIONS
   ============================================== */

/**
 * Função genérica para fazer requisições HTTP
 * @param {string} endpoint - Caminho da API (ex: '/api/users/')
 * @param {object} options - Opções do fetch (method, body, headers)
 * @returns {Promise<object>} - Resposta JSON da API
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;
    
    // Define headers padrão
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    
    // Configuração completa da requisição
    const config = {
        ...options,
        headers,
    };
    
    try {
        console.log(`🌐 API Request: ${options.method || 'GET'} ${endpoint}`);
        
        const response = await fetch(url, config);
        
        // Verifica se a resposta é OK (status 200-299)
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`✅ API Response:`, data);
        return data;
        
    } catch (error) {
        console.error(`❌ API Error (${endpoint}):`, error);
        throw error;
    }
}

/* ==============================================
   USER ENDPOINTS
   ============================================== */

/**
 * Obtém lista de todos os utilizadores
 * @returns {Promise<Array>} - Array de objetos de utilizadores
 */
async function getUsers() {
    return apiRequest('/api/users/?skip=0&limit=10');
}

/**
 * Obtém um utilizador específico pelo email
 * @param {string} email - Email do utilizador
 * @returns {Promise<object>} - Objeto do utilizador
 */
async function getUserByEmail(email) {
    const encodedEmail = encodeURIComponent(email);
    return apiRequest(`/api/users/email/${encodedEmail}`);
}

/**
 * Obtém os cartões de um utilizador
 * @param {string} userId - ID do utilizador
 * @returns {Promise<Array>} - Array de cartões
 */
async function getUserCards(userId) {
    return apiRequest(`/api/users/${userId}/cards`);
}

/* ==============================================
   TRANSACTION ENDPOINTS
   ============================================== */

/**
 * Cria uma nova transação
 * @param {object} transactionData - Dados da transação
 * @param {string} transactionData.user_id - ID do utilizador
 * @param {string} transactionData.card_id - ID do cartão
 * @param {number} transactionData.amount - Valor da transação
 * @param {string} transactionData.type - Tipo: "purchase" | "transfer"
 * @param {object} transactionData.location - {lat, lon, city, country}
 * @param {object} transactionData.merchant - (opcional) dados do comerciante
 * @returns {Promise<object>} - Objeto da transação criada + análise de risco
 */
async function createTransaction(transactionData) {
    return apiRequest('/api/transactions/', {
        method: 'POST',
        body: JSON.stringify(transactionData),
    });
}

/**
 * Obtém detalhes de uma transação específica
 * @param {string} transactionId - ID da transação
 * @returns {Promise<object>} - Objeto da transação
 */
async function getTransaction(transactionId) {
    return apiRequest(`/api/transactions/${transactionId}`);
}

/**
 * Atualiza uma transação com dados de liveness
 * @param {string} transactionId - ID da transação
 * @param {object} livenessData - Dados da verificação
 * @param {boolean} livenessData.liveness_passed - Se passou na verificação
 * @param {number} livenessData.challenges_completed - Número de desafios completados
 * @param {number} livenessData.heart_rate - Batimento cardíaco (BPM)
 * @param {number} livenessData.confidence_score - Score de confiança (0-1)
 * @returns {Promise<object>} - Transação atualizada
 */
async function updateTransactionLiveness(transactionId, livenessData) {
    return apiRequest(`/api/transactions/${transactionId}/liveness`, {
        method: 'PATCH',
        body: JSON.stringify(livenessData),
    });
}

/* ==============================================
   LIVENESS ENDPOINTS
   ============================================== */

/**
 * Obtém os requisitos de liveness para uma transação
 * @param {string} transactionId - ID da transação
 * @returns {Promise<object>} - Requisitos (challenges, timeout, etc.)
 */
async function getLivenessRequirements(transactionId) {
    return apiRequest(`/api/liveness/requirements/${transactionId}`);
}

/**
 * Simula uma verificação de liveness (para testes)
 * @param {boolean} success - Se deve retornar sucesso ou falha
 * @returns {Promise<object>} - Resultado simulado
 */
async function simulateLiveness(success = true) {
    return apiRequest(`/api/liveness/simulate?success=${success}`, {
        method: 'POST',
    });
}

/**
 * Verifica o status de liveness de uma transação
 * @param {string} transactionId - ID da transação
 * @returns {Promise<object>} - Status da verificação
 */
async function getLivenessStatus(transactionId) {
    return apiRequest(`/api/liveness/status/${transactionId}`);
}

/* ==============================================
   MERCHANT ENDPOINTS (Opcional - para features futuras)
   ============================================== */

/**
 * Obtém comerciantes próximos
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @param {number} radius - Raio em km
 * @returns {Promise<Array>} - Array de comerciantes
 */
async function getNearbyMerchants(lat, lon, radius = 50) {
    return apiRequest(`/api/merchants/nearby?lat=${lat}&lon=${lon}&radius_km=${radius}`);
}

/* ==============================================
   HEALTH CHECK
   ============================================== */

/**
 * Verifica se a API está disponível
 * @returns {Promise<object>} - Status do servidor
 */
async function checkHealth() {
    return apiRequest('/health');
}

/* ==============================================
   EXPORT (para usar em outros ficheiros)
   ============================================== */

// Não é necessário export em JS vanilla (tudo é global)
// Mas documentamos aqui as funções disponíveis:
console.log('✅ API Module Loaded');
console.log('📡 Available functions:', [
    'getUsers()',
    'getUserByEmail(email)',
    'getUserCards(userId)',
    'createTransaction(data)',
    'getTransaction(id)',
    'updateTransactionLiveness(id, data)',
    'getLivenessRequirements(id)',
    'simulateLiveness(success)',
    'getLivenessStatus(id)',
    'getNearbyMerchants(lat, lon, radius)',
    'checkHealth()',
]);
