/* ==============================================
   BioTrust - Main Application Logic
   ==============================================
   
   Este é o ficheiro principal que coordena toda a aplicação:
   - Carregamento inicial de utilizadores
   - Gestão do dashboard
   - Fluxo de transações
   - Navegação entre seções
   
   FLUXO COMPLETO:
   1. User seleciona uma conta → Dashboard aparece
   2. User clica "Enviar Dinheiro" → Form de transação
   3. User preenche e submete → API cria transação
   4. Se risco ALTO → Ativa webcam para liveness
   5. Após verificação → Transação aprovada/rejeitada
   
   ============================================== */

// ========== VERSÃO ==========
console.log('🚀 BioTrust App.js v3.2 - LivenessDetectorV3 Fixed (Window Visibility Issue)');

// ========== ESTADO GLOBAL DA APLICAÇÃO ==========
let currentUser = null;
let currentCard = null;
let pendingTransaction = null;

// ========== INICIALIZAÇÃO ==========

/**
 * Função chamada quando a página carrega
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 BioTrust App Inicializada');
    
    // Verifica se a API está online
    try {
        showLoading('Conectando ao servidor...');
        await checkHealth();
        console.log('✅ API está online');
        hideLoading();
    } catch (error) {
        hideLoading();
        showError('❌ Não foi possível conectar à API. Certifique-se de que o servidor FastAPI está a correr em http://localhost:8000');
        return;
    }
    
    // Carrega lista de utilizadores
    await loadUsers();
});

/* ==============================================
   USER MANAGEMENT
   ============================================== */

/**
 * Carrega e exibe lista de utilizadores
 */
async function loadUsers() {
    try {
        showLoading('Carregando utilizadores...');
        
        const users = await getUsers();
        
        hideLoading();
        
        if (!users || users.length === 0) {
            showError('Nenhum utilizador encontrado na base de dados.');
            return;
        }
        
        displayUserList(users);
        
    } catch (error) {
        hideLoading();
        showError('Erro ao carregar utilizadores: ' + error.message);
    }
}

/**
 * Exibe a lista de utilizadores na UI
 * @param {Array} users - Array de utilizadores
 */
function displayUserList(users) {
    const userListEl = document.getElementById('user-list');
    userListEl.innerHTML = '';
    
    users.forEach(user => {
        const userCard = document.createElement('div');
        userCard.className = 'user-card bg-white border-2 border-gray-200 hover:border-indigo-600 rounded-xl p-4 cursor-pointer';
        userCard.onclick = () => selectUser(user);
        
        userCard.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                    <i class="fas fa-user text-indigo-600 text-xl"></i>
                </div>
                <div>
                    <p class="font-semibold text-gray-800">${user.name}</p>
                    <p class="text-sm text-gray-500">${user.email}</p>
                </div>
            </div>
        `;
        
        userListEl.appendChild(userCard);
    });
}

/**
 * Seleciona um utilizador e mostra o dashboard
 * @param {object} user - Objeto do utilizador
 */
async function selectUser(user) {
    console.log('👤 Utilizador selecionado:', user.name);
    
    try {
        showLoading('Carregando dashboard...');
        
        // Busca dados completos do utilizador
        currentUser = await getUserByEmail(user.email);
        
        // Busca cartões
        const cards = await getUserCards(currentUser._id);
        console.log('📇 Cartões encontrados:', cards);
        
        if (!cards || cards.length === 0) {
            console.warn('⚠️ Nenhum cartão encontrado para este utilizador');
            currentCard = null;
        } else {
            currentCard = cards.find(card => card.is_default) || cards[0];
            console.log('💳 Cartão selecionado:', currentCard);
        }
        
        hideLoading();
        
        // Atualiza UI
        updateDashboard();
        
        // Navega para o dashboard
        showSection('dashboard');
        
    } catch (error) {
        hideLoading();
        showError('Erro ao carregar utilizador: ' + error.message);
    }
}

/**
 * Atualiza o dashboard com dados do utilizador
 */
function updateDashboard() {
    // Nome do utilizador
    document.getElementById('user-name').textContent = currentUser.name;
    
    // Saldo (calculado ficticiamente - em produção viria da BD)
    const balance = calculateBalance();
    document.getElementById('account-balance').textContent = `€${balance.toFixed(2)}`;
    
    // Cartão
    if (currentCard) {
        // API retorna 'last_four' por segurança (não o número completo)
        const lastFourDigits = currentCard.last_four || '0000';
        document.getElementById('card-number').textContent = `•••• •••• •••• ${lastFourDigits}`;
        document.getElementById('card-holder').textContent = currentCard.card_holder || 'N/A';
        document.getElementById('card-expiry').textContent = `${String(currentCard.expiry_month).padStart(2, '0')}/${currentCard.expiry_year}`;
        
        // Ícone do cartão
        const brandIcon = document.getElementById('card-brand');
        brandIcon.className = '';
        if (currentCard.card_type === 'visa') {
            brandIcon.className = 'fab fa-cc-visa text-3xl';
        } else if (currentCard.card_type === 'mastercard') {
            brandIcon.className = 'fab fa-cc-mastercard text-3xl';
        } else if (currentCard.card_type === 'amex') {
            brandIcon.className = 'fab fa-cc-amex text-3xl';
        }
    } else {
        // Sem cartão cadastrado
        document.getElementById('card-number').textContent = '•••• •••• •••• ••••';
        document.getElementById('card-holder').textContent = 'SEM CARTÃO';
        document.getElementById('card-expiry').textContent = '••/••';
        document.getElementById('card-brand').className = 'fas fa-credit-card text-3xl';
    }
    
    // Perfil de risco
    document.getElementById('account-age').textContent = `${currentUser.account_age_days} dias`;
    document.getElementById('avg-transaction').textContent = `€${currentUser.average_transaction.toFixed(2)}`;
    document.getElementById('home-location').textContent = `${currentUser.home_location.city}, ${currentUser.home_location.country}`;
    document.getElementById('verification-status').textContent = currentUser.is_verified ? '✅ Verificado' : '❌ Não Verificado';
}

/**
 * Calcula saldo fictício (em produção viria da BD)
 */
function calculateBalance() {
    // Saldo fictício baseado na média de transação
    return currentUser.average_transaction * 50;
}

/* ==============================================
   TRANSACTION FLOW
   ============================================== */

/**
 * Mostra o formulário de nova transação
 */
function showTransactionForm() {
    showSection('transaction-form');
}

/**
 * Esconde o formulário de transação
 */
function hideTransactionForm() {
    showSection('dashboard');
    document.getElementById('amount').value = '';
    document.getElementById('recipient').value = '';
}

/**
 * Submete uma nova transação
 * @param {Event} event - Evento do formulário
 */
async function submitTransaction(event) {
    event.preventDefault();
    
    // Verificar se há cartão
    if (!currentCard) {
        showError('Este utilizador não tem cartões cadastrados. Não é possível criar transação.');
        return;
    }
    
    // Obter valores do formulário
    const amount = parseFloat(document.getElementById('amount').value);
    const recipient = document.getElementById('recipient').value;
    const locationOption = document.getElementById('location').value;
    
    console.log('💸 Criando transação:', { amount, recipient, locationOption });
    console.log('💳 Cartão atual:', currentCard);
    console.log('👤 Utilizador atual:', currentUser);
    
    try {
        showLoading('Analisando risco da transação...');
        
        // Calcular localização baseada na opção selecionada
        const location = calculateLocationFromOption(locationOption);
        
        // Dados da transação no formato correto para a API
        const transactionData = {
            user_id: currentUser._id,
            card_id: currentCard._id,
            amount: amount,
            type: 'transfer',  // Tipo de transação (enum)
            description: `Transferência para ${recipient}`,
            user_location: {   // API espera user_location com lat/lon
                lat: location.lat,
                lon: location.lon
            },
            merchant_id: null  // Opcional para transferências
        };
        
        console.log('📤 Enviando transação:', transactionData);
        
        // Criar transação via API
        const result = await createTransaction(transactionData);
        
        hideLoading();
        
        console.log('✅ Transação criada:', result);
        console.log('📊 Risk Score:', result.risk_score);
        console.log('🎯 Risk Level:', result.risk_level);
        console.log('🔐 Liveness Required:', result.liveness_required);
        
        // Guarda transação pendente
        pendingTransaction = result;
        
        // Mostra resultado
        showTransactionResult(result, false);
        
    } catch (error) {
        hideLoading();
        showError('Erro ao criar transação: ' + error.message);
    }
}

/**
 * Calcula coordenadas baseadas na opção selecionada
 */
function calculateLocationFromOption(option) {
    const home = currentUser.home_location;
    
    switch (option) {
        case 'home':
            return { ...home };
        
        case 'nearby':
            // 50km de distância (aproximadamente 0.5 graus)
            return {
                city: 'Próxima',
                country: home.country,
                lat: home.lat + 0.5,
                lon: home.lon + 0.5
            };
        
        case 'far':
            // 200km+ (aproximadamente 2 graus)
            return {
                city: 'Madrid',
                country: 'Spain',
                lat: 40.4168,
                lon: -3.7038
            };
        
        case 'very_far':
            // 500km+ (Paris)
            return {
                city: 'Paris',
                country: 'France',
                lat: 48.8566,
                lon: 2.3522
            };
        
        default:
            return { ...home };
    }
}

/**
 * Mostra o resultado da transação
 * @param {object} transaction - Dados da transação
 * @param {boolean} afterLiveness - Se está mostrando após liveness
 */
function showTransactionResult(transaction, afterLiveness = false) {
    const resultSection = document.getElementById('transaction-result');
    const iconEl = document.getElementById('result-icon');
    const titleEl = document.getElementById('result-title');
    const messageEl = document.getElementById('result-message');
    const riskScoreEl = document.getElementById('risk-score');
    const riskLevelEl = document.getElementById('risk-level');
    const livenessRequiredEl = document.getElementById('liveness-required');
    const livenessBtn = document.getElementById('start-liveness-btn');
    
    // Determina o resultado
    const status = transaction.status;
    const riskScore = transaction.risk_score || 0;  // Backend retorna diretamente, não em risk_analysis
    const riskLevel = transaction.risk_level || 'low';  // Backend retorna diretamente
    const livenessRequired = transaction.liveness_required;
    
    // Atualiza ícone e título
    if (status === 'approved') {
        iconEl.innerHTML = '<div class="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto result-icon"><i class="fas fa-check text-5xl text-green-600"></i></div>';
        titleEl.textContent = '✅ Transação Aprovada!';
        titleEl.className = 'text-2xl font-bold mb-2 text-green-600';
        messageEl.textContent = 'A sua transferência foi processada com sucesso.';
    } else if (status === 'pending') {
        iconEl.innerHTML = '<div class="w-24 h-24 bg-yellow-100 rounded-full flex items-center justify-center mx-auto result-icon"><i class="fas fa-exclamation-triangle text-5xl text-yellow-600"></i></div>';
        titleEl.textContent = '⚠️ Verificação Necessária';
        titleEl.className = 'text-2xl font-bold mb-2 text-yellow-600';
        messageEl.textContent = 'Esta transação requer verificação biométrica para ser aprovada.';
    } else {
        iconEl.innerHTML = '<div class="w-24 h-24 bg-red-100 rounded-full flex items-center justify-center mx-auto result-icon"><i class="fas fa-times text-5xl text-red-600"></i></div>';
        titleEl.textContent = '❌ Transação Rejeitada';
        titleEl.className = 'text-2xl font-bold mb-2 text-red-600';
        messageEl.textContent = 'A transação não pôde ser processada.';
    }
    
    // Atualiza detalhes de risco
    riskScoreEl.textContent = `${riskScore}/100`;
    riskScoreEl.className = `font-bold ${riskLevel === 'high' ? 'text-red-600' : riskLevel === 'medium' ? 'text-yellow-600' : 'text-green-600'}`;
    
    riskLevelEl.textContent = riskLevel.toUpperCase();
    riskLevelEl.className = `risk-badge risk-${riskLevel}`;
    
    livenessRequiredEl.textContent = livenessRequired ? '✅ Sim' : '❌ Não';
    
    // Mostra/esconde botão de liveness
    if (livenessRequired && status === 'pending' && !afterLiveness) {
        livenessBtn.classList.remove('hidden');
    } else {
        livenessBtn.classList.add('hidden');
    }
    
    // Mostra seção
    showSection('transaction-result');
}

/**
 * Inicia verificação de liveness
 * CHAMA O LIVENESS_DETECTOR_V3.PY DIRETAMENTE NO SERVIDOR
 */
async function startLivenessVerification() {
    console.log('🎥 Iniciando verificação biométrica...');
    console.log('📋 Transação pendente:', pendingTransaction);
    
    if (!pendingTransaction) {
        showError('Nenhuma transação pendente encontrada.');
        return;
    }
    
    try {
        showLoading('⏳ Iniciando verificação biométrica...\n\n📹 Uma janela OpenCV vai abrir no seu ecrã.\n\n✋ NÃO feche o browser - aguarde!\n\n👀 Olhe para a janela OpenCV e siga as instruções lá.');
        
        // Chama o endpoint que executa detector.verify() no servidor
        const response = await fetch(`/api/liveness/verify/${pendingTransaction._id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        hideLoading();
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Falha na verificação');
        }
        
        const result = await response.json();
        
        console.log('✅ Resultado da verificação:', result);
        
        // Atualizar transação com resultado
        if (result.transaction) {
            pendingTransaction = result.transaction;
            showTransactionResult(result.transaction, true);
        } else if (result.success) {
            alert('✅ Verificação biométrica APROVADA!\n\nTodos os desafios completados com sucesso.');
            backToDashboard();
        } else {
            // Mostrar detalhes do erro
            let errorMsg = '❌ Verificação biométrica FALHOU\n\n';
            errorMsg += `Motivo: ${result.message}\n\n`;
            if (result.liveness_details && result.liveness_details.challenges_completed) {
                errorMsg += `Desafios completados: ${result.liveness_details.challenges_completed.length}`;
            }
            alert(errorMsg);
        }
        
    } catch (error) {
        hideLoading();
        console.error('❌ Erro:', error);
        showError('Erro na verificação biométrica: ' + error.message);
    }
}

/**
 * Volta ao dashboard
 */
function backToDashboard() {
    pendingTransaction = null;
    showSection('dashboard');
}

/**
 * Mostra histórico de transações (TODO)
 */
function showTransactionHistory() {
    alert('📋 Funcionalidade em desenvolvimento!\n\nAqui será exibido o histórico completo de transações do utilizador.');
}

/* ==============================================
   NAVIGATION
   ============================================== */

/**
 * Mostra uma seção específica e esconde as outras
 * @param {string} sectionId - ID da seção a mostrar
 */
function showSection(sectionId) {
    const sections = ['user-selection', 'dashboard', 'transaction-form', 'transaction-result'];
    
    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (id === sectionId) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        }
    });
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ==============================================
   UI HELPERS
   ============================================== */

/**
 * Mostra overlay de loading
 * @param {string} text - Texto a exibir
 */
function showLoading(text = 'Carregando...') {
    const overlay = document.getElementById('loading-overlay');
    const textEl = document.getElementById('loading-text');
    
    textEl.textContent = text;
    overlay.classList.remove('hidden');
}

/**
 * Esconde overlay de loading
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.add('hidden');
}

/**
 * Mostra mensagem de erro
 * @param {string} message - Mensagem de erro
 */
function showError(message) {
    alert('❌ ERRO\n\n' + message);
    console.error('❌', message);
}

/**
 * Mostra mensagem informativa
 * @param {string} message - Mensagem
 */
function showInfo(message) {
    alert('ℹ️ INFORMAÇÃO\n\n' + message);
    console.info('ℹ️', message);
}

/* ==============================================
   LIVENESS UI HELPERS
   ============================================== */

/**
 * Mostra o modal de liveness
 */
function showLivenessModal() {
    const modal = document.getElementById('liveness-modal');
    if (modal) {
        modal.classList.remove('hidden');
        console.log('🎥 Modal de liveness mostrado');
    } else {
        console.error('❌ Modal de liveness não encontrado!');
    }
}

/**
 * Esconde o modal de liveness
 */
function hideLivenessModal() {
    const modal = document.getElementById('liveness-modal');
    if (modal) {
        modal.classList.add('hidden');
        console.log('🚫 Modal de liveness escondido');
    }
}

/**
 * Simula o fluxo de liveness para testes
 * (Depois substituímos pela integração real)
 */
async function simulateLivenessFlow(transactionId) {
    console.log('🎭 Simulando fluxo de liveness para transação:', transactionId);
    
    try {
        // Simula alguns passos
        updateChallengeUI('Olhe para a câmara...', 'Processando...');
        await sleep(1500);
        
        updateChallengeUI('Vire a cabeça para a esquerda', 'Analisando...');
        updateProgress(33);
        await sleep(1500);
        
        updateChallengeUI('Vire a cabeça para a direita', 'Analisando...');
        updateProgress(66);
        await sleep(1500);
        
        updateChallengeUI('Sorria!', 'Finalizando...');
        updateProgress(100);
        await sleep(1500);
        
        // Simula sucesso
        const result = await simulateLiveness(true);
        console.log('✅ Liveness simulado com sucesso:', result);
        
        hideLoading();
        hideLivenessModal();
        
        // Atualiza transação para aprovada
        pendingTransaction.status = 'approved';
        pendingTransaction.liveness_verified = true;
        
        showTransactionResult(pendingTransaction, true);
        
    } catch (error) {
        console.error('❌ Erro na simulação:', error);
        showError('Erro na verificação: ' + error.message);
        hideLivenessModal();
    }
}

/**
 * Atualiza UI de desafio
 */
function updateChallengeUI(instruction, status) {
    const instructionEl = document.getElementById('challenge-instruction');
    const statusEl = document.getElementById('challenge-status');
    
    if (instructionEl) instructionEl.textContent = instruction;
    if (statusEl) statusEl.textContent = status;
}

/**
 * Atualiza progresso
 */
function updateProgress(percent) {
    const progressBar = document.getElementById('liveness-progress');
    if (progressBar) {
        progressBar.style.width = percent + '%';
    }
}

/**
 * Helper para sleep
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/* ==============================================
   INITIALIZATION
   ============================================== */

// Exportar funções para uso em outros módulos (webcam.js)
window.showTransactionResult = showTransactionResult;
window.showError = showError;
window.showInfo = showInfo;

console.log('✅ App Module Loaded');
console.log('🚀 BioTrust Web App Ready!');
