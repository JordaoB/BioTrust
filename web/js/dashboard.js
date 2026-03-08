/**
 * BioTrust Dashboard - Lógica Principal
 * v1.0 - MBWay Style Interface
 */

const API_BASE = '';
let currentUser = null;
let sessionToken = null;
let contacts = [];
let userCards = [];

// Location mappings
const LOCATIONS = {
    'home': { city: 'Lisboa', lat: 38.7223, lon: -9.1393 },
    'nearby': { city: 'Queluz', lat: 38.7567, lon: -9.2544 },
    'far': { city: 'Porto', lat: 41.1579, lon: -8.6291 },
    'very-far': { city: 'Faro', lat: 37.0194, lon: -7.9322 }
};

// Initialize dashboard
window.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    sessionToken = localStorage.getItem('session_token');
    if (!sessionToken) {
        window.location.href = '/web';
        return;
    }
    
    // Load user data
    const userData = localStorage.getItem('user');
    if (userData) {
        currentUser = JSON.parse(userData);
        updateUI();
    }
    
    // Verify session and load data
    await verifySession();
    await loadUserData();
    await loadCards();
    await loadContacts();
    await loadTransactions();
});

// Verify session is still valid
async function verifySession() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/session/${sessionToken}`);
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            logout();
        } else {
            currentUser = data.user;
            localStorage.setItem('user', JSON.stringify(currentUser));
            updateUI();
        }
    } catch (error) {
        console.error('Session verification error:', error);
        logout();
    }
}

// Update UI with user data
function updateUI() {
    if (currentUser) {
        document.getElementById('user-name').textContent = currentUser.name.split(' ')[0];
        
        // Calculate total balance from all cards
        let totalBalance = 0;
        if (userCards && userCards.length > 0) {
            totalBalance = userCards.reduce((sum, card) => sum + (card.balance || 0), 0);
        }
        
        document.getElementById('balance').textContent = `€ ${totalBalance.toFixed(2)}`;
    }
}

// Load user data
async function loadUserData() {
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser._id}`);
        const user = await response.json();
        currentUser = { ...currentUser, ...user };
        localStorage.setItem('user', JSON.stringify(currentUser));
        updateUI();
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

// Load cards
async function loadCards() {
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser._id}/cards`);
        const data = await response.json();
        
        if (data.success && data.cards) {
            userCards = data.cards;
            displayCards(data.cards);
            updateUI();  // Update UI to recalculate balance
        }
    } catch (error) {
        console.error('Error loading cards:', error);
        document.getElementById('cards-container').innerHTML = `
            <div class="text-center text-gray-500" style="min-width: 320px">
                <p>Nenhum cartão adicionado</p>
                <button onclick="openAddCardModal()" class="mt-4 text-green-600 font-semibold">
                    <i class="fas fa-plus mr-2"></i>Adicionar Cartão
                </button>
            </div>
        `;
    }
}

// Display cards
function displayCards(cards) {
    const container = document.getElementById('cards-container');
    
    if (!cards || cards.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-500" style="min-width: 320px">
                <p>Nenhum cartão adicionado</p>
                <button onclick="openAddCardModal()" class="mt-4 text-green-600 font-semibold">
                    <i class="fas fa-plus mr-2"></i>Adicionar Cartão
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = cards.map((card, index) => `
        <div class="payment-card card-${card.card_type} fade-in">
            <div class="flex justify-between items-start mb-6">
                <div class="text-sm opacity-90">
                    ${card.card_type === 'visa' ? 'VISA' : card.card_type === 'mastercard' ? 'MASTERCARD' : 'AMEX'}
                </div>
                ${card.is_default ? '<div class="bg-white bg-opacity-20 px-3 py-1 rounded-full text-xs">Principal</div>' : ''}
            </div>
            
            <div class="mb-2">
                <div class="text-xs opacity-75 mb-1">Saldo Disponível</div>
                <div class="text-2xl font-bold">€ ${(card.balance || 0).toFixed(2)}</div>
            </div>
            
            <div class="mb-6">
                <div class="text-lg font-mono tracking-wider">
                    ${card.masked_number || `**** **** **** ${card.last_four}`}
                </div>
            </div>
            
            <div class="flex justify-between items-end">
                <div>
                    <div class="text-xs opacity-75 mb-1">Titular</div>
                    <div class="text-sm font-semibold">${card.card_holder}</div>
                </div>
                <div class="text-right">
                    <div class="text-xs opacity-75 mb-1">Validade</div>
                    <div class="text-sm font-semibold">${card.expiry}</div>
                </div>
            </div>
            
            <div class="mt-3 text-xs opacity-75">
                Limite diário: €${(card.daily_limit || 0).toFixed(0)} | Gasto hoje: €${(card.daily_spent || 0).toFixed(2)}
            </div>
            
            ${!card.is_default ? `
                <button 
                    onclick="deleteCard(${index})" 
                    class="absolute top-4 right-4 text-white bg-white bg-opacity-20 hover:bg-opacity-30 w-8 h-8 rounded-full flex items-center justify-center"
                >
                    <i class="fas fa-trash text-sm"></i>
                </button>
            ` : ''}
        </div>
    `).join('');
}

// Load contacts
async function loadContacts() {
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser._id}/contacts`);
        const data = await response.json();
        
        if (data.success && data.contacts) {
            contacts = data.contacts;
            updateContactsDropdown();
        }
    } catch (error) {
        console.error('Error loading contacts:', error);
    }
}

// Update contacts dropdown
function updateContactsDropdown() {
    const select = document.getElementById('recipient-select');
    select.innerHTML = '<option value="">Selecione um contacto</option>' +
        contacts.map(contact => `
            <option value="${contact.email}">
                ${contact.name} (${contact.phone})
            </option>
        `).join('');
}

// Load transactions
async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser._id}/transactions?limit=5`);
        const data = await response.json();
        
        if (data && Array.isArray(data)) {
            displayTransactions(data);
        } else if (data && data.transactions) {
            displayTransactions(data.transactions);
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
        // Show empty state
        displayTransactions([]);
    }
}

// Display transactions
function displayTransactions(transactions) {
    const container = document.getElementById('transactions-container');
    
    if (!transactions || transactions.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-500 py-8">
                <svg style="width: 64px; height: 64px; margin: 0 auto 16px; color: #d1d5db;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                </svg>
                <p class="text-lg font-semibold mb-2">Sem transações</p>
                <p class="text-sm">As suas transações aparecerão aqui</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = transactions.map(tx => {
        const isExpense = tx.type === 'transfer' || tx.type === 'payment';
        const statusColors = {
            'approved': 'text-green-600',
            'pending': 'text-yellow-600',
            'rejected': 'text-red-600',
            'blocked': 'text-red-600'
        };
        const statusIcons = {
            'approved': '✓',
            'pending': '⏱',
            'rejected': '✗',
            'blocked': '🚫'
        };
        
        return `
            <div class="transaction-item fade-in" style="
                background: white;
                padding: 16px;
                border-radius: 12px;
                margin-bottom: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            ">
                <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                    <div style="
                        width: 40px;
                        height: 40px;
                        border-radius: 50%;
                        background: ${isExpense ? '#fee2e2' : '#dcfce7'};
                        color: ${isExpense ? '#dc2626' : '#16a34a'};
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 18px;
                    ">
                        ${isExpense ? '↑' : '↓'}
                    </div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #1f2937; margin-bottom: 2px;">
                            ${tx.merchant_name || tx.recipient_email || 'Transação'}
                        </div>
                        <div style="font-size: 12px; color: #6b7280;">
                            ${new Date(tx.timestamp || tx.created_at).toLocaleDateString('pt-PT', { 
                                day: '2-digit', 
                                month: 'short', 
                                hour: '2-digit', 
                                minute: '2-digit' 
                            })}
                            ${tx.risk_score ? `• Risco: ${tx.risk_score}` : ''}
                        </div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="
                        font-weight: 700;
                        font-size: 16px;
                        color: ${isExpense ? '#dc2626' : '#16a34a'};
                        margin-bottom: 4px;
                    ">
                        ${isExpense ? '-' : '+'}€${parseFloat(tx.amount).toFixed(2)}
                    </div>
                    <div class="${statusColors[tx.status] || 'text-gray-600'}" style="font-size: 12px; font-weight: 600;">
                        ${statusIcons[tx.status] || ''} ${tx.status || 'pending'}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Handle send money
async function handleSendMoney(event) {
    event.preventDefault();
    
    const recipientEmail = document.getElementById('recipient-select').value;
    const amount = parseFloat(document.getElementById('amount-input').value);
    const locationKey = document.getElementById('location-select').value;
    
    const recipient = contacts.find(c => c.email === recipientEmail);
    if (!recipient) {
        showError('Contacto inválido');
        return;
    }
    
    const location = LOCATIONS[locationKey];
    
    // Create transaction
    showLoading('Criando transação...');
    
    try {
        const response = await fetch(`${API_BASE}/api/transactions/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: currentUser._id,
                card_id: userCards.find(c => c.is_default)?._id || userCards[0]?._id,
                amount: amount,
                type: 'transfer',
                recipient_email: recipientEmail,
                user_location: location
            })
        });
        
        const transaction = await response.json();
        
        if (!response.ok) {
            throw new Error(transaction.detail || 'Erro ao criar transação');
        }
        
        console.log('Transaction created:', transaction);
        
        hideLoading();
        
        // Check if liveness verification is required
        if (transaction.liveness_required) {
            closeSendMoneyModal();
            showLivenessVerification(transaction);
        } else {
            // Transaction approved automatically
            closeSendMoneyModal();
            showSuccess(`Transação de €${amount.toFixed(2)} enviada para ${recipient.name}!`);
            await loadUserData();
            await loadTransactions();
            
            // Clear form
            document.getElementById('send-money-form').reset();
        }
    } catch (error) {
        console.error('Transaction error:', error);
        hideLoading();
        showError(error.message);
    }
}

// Show liveness verification
function showLivenessVerification(transaction) {
    showLoading(`
        <div class="text-center">
            <div class="text-6xl mb-4">🔐</div>
            <h3 class="text-2xl font-bold mb-4">Verificação Biométrica Requerida</h3>
            <p class="text-gray-600 mb-2">Risco: ${transaction.risk_score}/100</p>
            <p class="text-gray-600 mb-6">Uma janela OpenCV vai abrir no servidor</p>
            <div class="animate-pulse">Aguarde...</div>
        </div>
    `);
    
    // Call liveness verification endpoint
    fetch(`${API_BASE}/api/liveness/verify/${transaction._id}`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(result => {
        hideLoading();
        
        if (result.success) {
            showSuccess(`
                <div class="text-center">
                    <div class="text-6xl mb-4">✅</div>
                    <h3 class="text-2xl font-bold mb-2">Verificação Completa!</h3>
                    <p class="text-gray-600">Transação de €${transaction.amount.toFixed(2)} aprovada</p>
                    <p class="text-sm text-gray-500 mt-2">Challenges completados: ${result.liveness_details?.challenges_completed?.length || 0}</p>
                </div>
            `);
            loadUserData();
            loadTransactions();
        } else {
            showError(`
                <div class="text-center">
                    <div class="text-6xl mb-4">❌</div>
                    <h3 class="text-2xl font-bold mb-2">Verificação Falhou</h3>
                    <p class="text-gray-600">${result.message}</p>
                </div>
            `);
        }
    })
    .catch(error => {
        hideLoading();
        showError('Erro na verificação biométrica');
        console.error('Liveness error:', error);
    });
}

// Handle add card
async function handleAddCard(event) {
    event.preventDefault();
    
    const cardNumber = document.getElementById('card-number').value.replace(/\s/g, '');
    const cardHolder = document.getElementById('card-holder').value;
    const cardMonth = parseInt(document.getElementById('card-month').value);
    const cardYear = parseInt(document.getElementById('card-year').value);
    const cardCvv = document.getElementById('card-cvv').value;
    const cardType = document.getElementById('card-type').value;
    
    showLoading('Adicionando cartão...');
    
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser._id}/cards`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                card_number: cardNumber,
                card_holder: cardHolder,
                expiry_month: cardMonth,
                expiry_year: cardYear,
                cvv: cardCvv,
                card_type: cardType,
                is_default: userCards.length === 0
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            hideLoading();
            closeAddCardModal();
            showSuccess('Cartão adicionado com sucesso!');
            await loadCards();
            
            // Clear form
            event.target.reset();
        } else {
            throw new Error(data.detail || 'Erro ao adicionar cartão');
        }
    } catch (error) {
        hideLoading();
        showError(error.message);
        console.error('Add card error:', error);
    }
}

// Delete card
async function deleteCard(cardIndex) {
    if (!confirm('Tem certeza que deseja remover este cartão?')) {
        return;
    }
    
    showLoading('Removendo cartão...');
    
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser._id}/cards/${cardIndex}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            hideLoading();
            showSuccess('Cartão removido com sucesso!');
            await loadCards();
        } else {
            throw new Error(data.detail || 'Erro ao remover cartão');
        }
    } catch (error) {
        hideLoading();
        showError(error.message);
    }
}

// Modal functions
function openSendMoneyModal() {
    document.getElementById('send-money-modal').classList.add('show');
}

function closeSendMoneyModal() {
    document.getElementById('send-money-modal').classList.remove('show');
}

function openAddCardModal() {
    document.getElementById('add-card-modal').classList.add('show');
}

function closeAddCardModal() {
    document.getElementById('add-card-modal').classList.remove('show');
}

// Tab switching
function switchTab(tab) {
    if (tab === 'cards') {
        window.location.href = '/static/cards.html';
    } else if (tab === 'profile') {
        window.location.href = '/static/profile.html';
    } else if (tab === 'home') {
        // Already on home, scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// View transaction history
function viewHistory() {
    window.location.href = '/static/transaction-history.html';
}

// Logout
function logout() {
    localStorage.clear();
    window.location.href = '/web';
}

// Helper functions - Elegant notifications
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = 'notification fade-in';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        min-width: 300px;
        max-width: 500px;
        background: white;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 12px;
        animation: slideInRight 0.3s ease-out;
    `;
    
    const icons = {
        success: '<svg style="color: #10b981; width: 24px; height: 24px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        error: '<svg style="color: #ef4444; width: 24px; height: 24px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        info: '<svg style="color: #3b82f6; width: 24px; height: 24px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
    };
    
    notification.innerHTML = `
        ${icons[type] || icons.info}
        <div style="flex: 1; color: #1f2937; font-size: 14px;">${message}</div>
        <button onclick="this.parentElement.remove()" style="color: #9ca3af; cursor: pointer; border: none; background: none; padding: 4px;">
            <svg style="width: 20px; height: 20px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function showLoading(message = 'Carregando...') {
    const modal = document.createElement('div');
    modal.id = 'loading-modal';
    modal.className = 'modal show';
    modal.style.cssText = 'display: flex; align-items: center; justify-content: center;';
    modal.innerHTML = `
        <div class="modal-content text-center" style="max-width: 400px; padding: 40px;">
            <div style="margin-bottom: 24px;">
                <svg style="width: 80px; height: 80px; color: #00A859; animation: spin 2s linear infinite;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle style="opacity: 0.25;" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path style="opacity: 0.75;" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            </div>
            <div style="font-size: 18px; color: #1f2937; font-weight: 500;">${message}</div>
        </div>
    `;
    document.body.appendChild(modal);
}

function hideLoading() {
    const modal = document.getElementById('loading-modal');
    if (modal) {
        modal.style.opacity = '0';
        setTimeout(() => modal.remove(), 200);
    }
}

// Add CSS animation keyframes
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

function showComingSoon() {
    showSuccess('Funcionalidade em desenvolvimento! 🚀');
}

// Auto-format card number input
document.addEventListener('DOMContentLoaded', () => {
    const cardNumberInput = document.getElementById('card-number');
    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\s/g, '');
            let formattedValue = value.match(/.{1,4}/g)?.join(' ') || value;
            e.target.value = formattedValue;
        });
    }
});
