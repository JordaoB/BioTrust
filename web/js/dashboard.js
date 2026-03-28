// API_BASE is defined in token-manager.js (loaded first)
let currentUser = null;
let accessToken = null;
let contacts = [];
let userCards = [];
let latestTransactions = [];
let riskChart = null;
let isSendingMoney = false;

const FACE_VERIFY_TIMEOUT_MS = 45000;
const CREATE_TX_TIMEOUT_MS = 30000;

async function fetchJsonWithTimeout(url, options = {}, timeoutMs = 30000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        const data = await response.json();
        return { response, data };
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request timed out. Please try again.');
        }
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

// Location mappings
const LOCATIONS = {
    'home': { city: 'Lisboa', lat: 38.7223, lon: -9.1393 },
    'nearby': { city: 'Queluz', lat: 38.7567, lon: -9.2544 },
    'far': { city: 'Porto', lat: 41.1579, lon: -8.6291 },
    'very-far': { city: 'Faro', lat: 37.0194, lon: -7.9322 }
};

function getBrowserPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by this browser'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => resolve(position),
            (error) => reject(error),
            {
                enableHighAccuracy: true,
                timeout: 7000,
                maximumAge: 60000,
            }
        );
    });
}

async function resolveRealtimeLocation() {
    const pos = await getBrowserPosition();
    const lat = pos.coords.latitude;
    const lon = pos.coords.longitude;

    try {
        const response = await fetch(`${API_BASE}/api/location/reverse?lat=${lat}&lon=${lon}`);
        const data = await response.json();
        if (response.ok) {
            return {
                city: data.city || 'GPS',
                country: data.country || 'Unknown',
                lat,
                lon,
            };
        }
    } catch (error) {
        console.warn('Reverse geocoding failed, using raw GPS coordinates', error);
    }

    return {
        city: 'GPS',
        country: 'Unknown',
        lat,
        lon,
    };
}

// Initialize dashboard
window.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    accessToken = TokenManager.getAccessToken();
    if (!accessToken) {
        window.location.href = '/web';
        return;
    }
    
    // Start auto-refresh
    TokenManager.startAutoRefresh();
    
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
    await loadFaceProfileBanner();
});

// Verify session is still valid
async function verifySession() {
    try {
        accessToken = TokenManager.getAccessToken();
        const response = await fetch(`${API_BASE}/api/auth/session/${accessToken}`);
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            // Try to refresh token
            const refreshed = await TokenManager.refreshAccessToken();
            if (!refreshed) {
                TokenManager.logout();
            } else {
                // Retry verification
                await verifySession();
            }
        } else {
            currentUser = data.user;
            localStorage.setItem('user', JSON.stringify(currentUser));
            updateUI();
        }
    } catch (error) {
        console.error('Session verification error:', error);
        TokenManager.logout();
    }
}

// Update UI with user data
function updateUI() {
    if (currentUser) {
        // Update navbar user name
        const firstName = currentUser.name.split(' ')[0];
        document.getElementById('user-name-nav').textContent = firstName;
    }
}

// Toggle user dropdown menu
function toggleUserMenu() {
    const dropdown = document.getElementById('user-dropdown');
    dropdown.classList.toggle('show');
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const userMenu = document.querySelector('.user-menu');
    if (userMenu && !userMenu.contains(e.target)) {
        document.getElementById('user-dropdown').classList.remove('show');
    }

    const modalIds = ['send-money-modal', 'add-card-modal', 'risk-explain-modal'];
    modalIds.forEach((modalId) => {
        const modal = document.getElementById(modalId);
        if (modal && e.target === modal) {
            modal.classList.remove('show');
        }
    });
});

document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') {
        return;
    }

    ['send-money-modal', 'add-card-modal', 'risk-explain-modal'].forEach((modalId) => {
        const modal = document.getElementById(modalId);
        if (modal && modal.classList.contains('show')) {
            modal.classList.remove('show');
        }
    });
});

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
            updateCardsDropdown();  // Add this
            updateUI();  // Update UI to recalculate balance
        }
    } catch (error) {
        console.error('Error loading cards:', error);
        document.getElementById('cards-container').innerHTML = `
            <div class="text-center text-gray-500" style="min-width: 320px">
                <p>No card added</p>
                <button onclick="openAddCardModal()" class="mt-4 text-green-600 font-semibold">
                    <i class="fas fa-plus mr-2"></i>Add Card
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
                <p>No card added</p>
                <button onclick="openAddCardModal()" class="mt-4 text-green-600 font-semibold">
                    <i class="fas fa-plus mr-2"></i>Add Card
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
                ${card.is_default ? '<div class="bg-white bg-opacity-20 px-3 py-1 rounded-full text-xs">Primary</div>' : ''}
            </div>
            
            <div class="mb-2">
                <div class="text-xs opacity-75 mb-1">Available Balance</div>
                <div class="text-2xl font-bold">€ ${(card.balance || 0).toFixed(2)}</div>
            </div>
            
            <div class="mb-6">
                <div class="text-lg font-mono tracking-wider">
                    ${card.masked_number || `**** **** **** ${card.last_four}`}
                </div>
            </div>
            
            <div class="flex justify-between items-end">
                <div>
                    <div class="text-xs opacity-75 mb-1">Cardholder</div>
                    <div class="text-sm font-semibold">${card.card_holder}</div>
                </div>
                <div class="text-right">
                    <div class="text-xs opacity-75 mb-1">Expiry</div>
                    <div class="text-sm font-semibold">${card.expiry}</div>
                </div>
            </div>
            
            <div class="mt-3 text-xs opacity-75">
                Daily limit: €${(card.daily_limit || 0).toFixed(0)} | Spent today: €${(card.daily_spent || 0).toFixed(2)}
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
    select.innerHTML = '<option value="">Select a contact</option>' +
        contacts.map(contact => `
            <option value="${contact.email}">
                ${contact.name} (${contact.phone})
            </option>
        `).join('');
}

// Update cards dropdown  
function updateCardsDropdown() {
    const select = document.getElementById('card-select');
    if (!select) return; // Element doesn't exist on all pages
    
    if (!userCards || userCards.length === 0) {
        select.innerHTML = '<option value="">No cards available</option>';
        return;
    }
    
    select.innerHTML = '<option value="">Select a card</option>' +
        userCards.map((card, index) => {
            const balance = card.balance || 0;
            const cardType = card.card_type === 'visa' ? 'VISA' : 
                           card.card_type === 'mastercard' ? 'Mastercard' : 'AMEX';
            const lastFour = card.last_four || card.masked_number?.slice(-4) || '****';
            const defaultLabel = card.is_default ? ' (Default)' : '';
            
            return `
                <option value="${index}" data-balance="${balance}">
                    ${cardType} **** ${lastFour}${defaultLabel} - €${balance.toFixed(2)}
                </option>
            `;
        }).join('');
    
    // Auto-select default card
    const defaultIndex = userCards.findIndex(c => c.is_default);
    if (defaultIndex !== -1) {
        select.value = defaultIndex.toString();
    }
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
    latestTransactions = transactions || [];
    
    if (!transactions || transactions.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-500 py-8">
                <svg style="width: 64px; height: 64px; margin: 0 auto 16px; color: #d1d5db;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                </svg>
                <p class="text-lg font-semibold mb-2">No transactions</p>
                <p class="text-sm">Your transactions will appear here</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = transactions.map((tx, index) => {
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
                            ${tx.merchant_name || tx.recipient_email || 'Transaction'}
                        </div>
                        <div style="font-size: 12px; color: #6b7280;">
                            ${new Date(tx.timestamp || tx.created_at).toLocaleDateString('pt-PT', { 
                                day: '2-digit', 
                                month: 'short', 
                                hour: '2-digit', 
                                minute: '2-digit' 
                            })}
                            ${tx.risk_score ? `• Risk: ${tx.risk_score}` : ''}
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
                    <button class="tx-explain-btn" data-index="${index}" style="margin-top: 6px; font-size: 12px; color: #0f766e; font-weight: 700; border: none; background: none; cursor: pointer;">
                        View explanation
                    </button>
                </div>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.tx-explain-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.dataset.index, 10);
            const tx = latestTransactions[idx];
            if (tx) {
                showRiskExplainModal(tx);
            }
        });
    });
}

function showRiskExplainModal(transaction) {
    const modal = document.getElementById('risk-explain-modal');
    const content = document.getElementById('risk-explain-content');

    const factors = transaction.risk_factors || {};
    const factorRows = [
        { key: 'location', label: 'Location' },
        { key: 'amount', label: 'Amount' },
        { key: 'velocity', label: 'Velocity' },
        { key: 'recipient', label: 'Recipient' },
        { key: 'time', label: 'Time' }
    ];

    const blockedText = transaction.status === 'rejected' || transaction.status === 'blocked'
        ? 'BLOQUEADO'
        : transaction.status === 'pending'
            ? 'IN REVIEW (LIVENESS)'
            : 'APPROVED';

    const anomalySummary = transaction.anomaly_detected
        ? `Isolation Forest detected ${Number(transaction.anomaly_score || 0).toFixed(1)}% anomaly`
        : 'Isolation Forest found no critical anomalies';

    const locationReason = (factors.location && factors.location.reason) || transaction.risk_reason || 'No location detail';
    const reasonLine = `${blockedText}: ${anomalySummary}. ${locationReason}`;

    const bars = factorRows.map(row => {
        const item = factors[row.key] || {};
        const score = Number(item.score || 0).toFixed(1);
        const contribution = Number(item.contribution || 0).toFixed(1);
        const detail = item.reason || 'No detail';
        return `
            <div class="mb-3">
                <div class="flex justify-between text-sm mb-1">
                    <span class="font-semibold text-gray-700">${row.label}</span>
                    <span class="text-gray-600">score ${score} • impact ${contribution}</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5 mb-1">
                    <div class="bg-gradient-to-r from-emerald-500 to-red-500 h-2.5 rounded-full" style="width: ${Math.min(100, Math.max(0, Number(score)))}%"></div>
                </div>
                <div class="text-xs text-gray-500">${detail}</div>
            </div>
        `;
    }).join('');

    content.innerHTML = `
        <div class="mb-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div class="text-sm text-gray-500 mb-1">Decision summary</div>
            <div class="text-lg font-bold text-slate-800">${reasonLine}</div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div class="p-3 rounded-xl bg-white border border-gray-200">
                <div class="text-xs text-gray-500">Risk Score</div>
                <div class="text-2xl font-extrabold text-gray-900">${Number(transaction.risk_score || 0).toFixed(1)}/100</div>
                <div class="text-sm text-gray-600">Level: ${String(transaction.risk_level || 'N/A').toUpperCase()}</div>
            </div>
            <div class="p-3 rounded-xl bg-white border border-gray-200">
                <canvas id="risk-factor-chart" height="120"></canvas>
            </div>
        </div>

        <div class="mb-2 text-sm font-bold text-gray-700">Top contributing factors</div>
        ${bars}

        <div class="mt-4 text-xs text-gray-500">
            TX: ${transaction._id || transaction.transaction_id || 'N/A'} • ${new Date(transaction.created_at || Date.now()).toLocaleString('en-GB')}
        </div>
    `;

    const chartCanvas = document.getElementById('risk-factor-chart');
    if (chartCanvas && typeof Chart !== 'undefined') {
        if (riskChart) {
            riskChart.destroy();
        }
        riskChart = new Chart(chartCanvas, {
            type: 'doughnut',
            data: {
                labels: factorRows.map(f => f.label),
                datasets: [
                    {
                        data: factorRows.map(f => Number((factors[f.key] || {}).contribution || 0)),
                        backgroundColor: ['#0ea5e9', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981'],
                        borderWidth: 0
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 10, font: { size: 10 } }
                    }
                },
                cutout: '65%'
            }
        });
    }

    modal.classList.add('show');
}

function closeRiskExplainModal() {
    document.getElementById('risk-explain-modal').classList.remove('show');
}

async function getFaceIdentityStatus(userId) {
    const { response, data } = await fetchJsonWithTimeout(
        `${API_BASE}/api/face-id/status/${userId}`,
        {},
        10000
    );
    if (!response.ok) {
        throw new Error(data.detail || 'Could not fetch face identity status');
    }
    return data;
}

function renderFaceProfileBanner(status) {
    const banner = document.getElementById('face-profile-banner');
    if (!banner) {
        return;
    }

    if (!status.available) {
        banner.className = 'rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm';
        banner.innerHTML = `
            <div class="flex items-center justify-between gap-3">
                <div>
                    <div class="font-semibold text-amber-900"><i class="fas fa-exclamation-triangle mr-2"></i>Facial Profile</div>
                    <div class="text-amber-800 mt-1">Face identity service unavailable right now.</div>
                </div>
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-600 text-white">UNAVAILABLE</span>
            </div>
        `;
        return;
    }

    if (!status.enrolled) {
        banner.className = 'rounded-2xl border border-sky-300 bg-sky-50 p-4 text-sm';
        banner.innerHTML = `
            <div class="flex items-center justify-between gap-3">
                <div>
                    <div class="font-semibold text-sky-900"><i class="fas fa-camera mr-2"></i>Facial Profile</div>
                    <div class="text-sky-800 mt-1">No master selfie yet. On your next transfer, you'll accept the terms and capture your first photo.</div>
                </div>
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-sky-600 text-white">PENDING</span>
            </div>
        `;
        return;
    }

    banner.className = 'rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-sm';
    banner.innerHTML = `
        <div class="flex items-center justify-between gap-3">
            <div>
                <div class="font-semibold text-emerald-900"><i class="fas fa-user-check mr-2"></i>Facial Profile</div>
                <div class="text-emerald-800 mt-1">Master selfie registered. Identity check is active before each transfer.</div>
            </div>
            <span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-600 text-white">REGISTERED</span>
        </div>
    `;
}

async function loadFaceProfileBanner() {
    if (!currentUser?._id) {
        return;
    }
    try {
        const status = await getFaceIdentityStatus(currentUser._id);
        renderFaceProfileBanner(status);
    } catch (error) {
        console.error('Error loading face profile status:', error);
        renderFaceProfileBanner({ available: false });
    }
}

function captureFaceSnapshotForIdentity(isFirstEnrollment = false) {
    return new Promise(async (resolve, reject) => {
        let stream = null;
        let modal = null;

        const cleanup = () => {
            if (stream) {
                stream.getTracks().forEach((track) => track.stop());
            }
            if (modal && modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        };

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
                audio: false
            });

            modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.82);
                z-index: 130;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 16px;
            `;

            modal.innerHTML = `
                <div style="background:#111827; border:1px solid #1f2937; width:min(520px,96vw); border-radius:16px; padding:16px; color:#fff;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <h3 style="font-size:18px; font-weight:700;">Selfie de Verificacao</h3>
                        <button id="face-cancel-btn" style="background:transparent; border:none; color:#9ca3af; cursor:pointer; font-size:20px;">&times;</button>
                    </div>
                    <p style="font-size:13px; color:#d1d5db; margin-bottom:10px;">Centralize o rosto e tire uma foto nítida.</p>
                    <div style="position:relative; width:100%; aspect-ratio:4/3; border-radius:12px; overflow:hidden; background:#000;">
                        <video id="face-capture-video" autoplay playsinline muted style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);"></video>
                        <img id="face-preview-image" src="" alt="Preview" style="display:none; width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" />
                    </div>
                    <p id="face-first-photo-warning" style="display:${isFirstEnrollment ? 'none' : 'none'}; margin-top:10px; font-size:12px; color:#fbbf24;">
                        Ao confirmar, esta selfie será definida como foto mestre e não poderá ser alterada pelo utilizador.
                    </p>
                    <div style="display:flex; gap:8px; margin-top:12px;">
                        <button id="face-take-btn" style="flex:1; background:#00A859; color:#fff; border:none; border-radius:10px; padding:10px 12px; font-weight:600; cursor:pointer;">Tirar Foto</button>
                        <button id="face-retry-btn" style="display:none; flex:1; background:#1f2937; color:#fff; border:none; border-radius:10px; padding:10px 12px; font-weight:600; cursor:pointer;">Tirar Novamente</button>
                        <button id="face-confirm-btn" style="display:none; flex:1; background:#16a34a; color:#fff; border:none; border-radius:10px; padding:10px 12px; font-weight:700; cursor:pointer;">Confirmar</button>
                        <button id="face-close-btn" style="background:#374151; color:#fff; border:none; border-radius:10px; padding:10px 12px; cursor:pointer;">Cancelar</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            const video = modal.querySelector('#face-capture-video');
            const preview = modal.querySelector('#face-preview-image');
            const warning = modal.querySelector('#face-first-photo-warning');
            const takeBtn = modal.querySelector('#face-take-btn');
            const retryBtn = modal.querySelector('#face-retry-btn');
            const confirmBtn = modal.querySelector('#face-confirm-btn');
            video.srcObject = stream;
            await video.play();

            let selectedImageBase64 = null;

            const cancel = () => {
                cleanup();
                reject(new Error('Captura de selfie cancelada'));
            };

            modal.querySelector('#face-cancel-btn').onclick = cancel;
            modal.querySelector('#face-close-btn').onclick = cancel;

            takeBtn.onclick = () => {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                const ctx = canvas.getContext('2d');

                ctx.translate(canvas.width, 0);
                ctx.scale(-1, 1);
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                selectedImageBase64 = canvas.toDataURL('image/jpeg', 0.88);

                preview.src = selectedImageBase64;
                preview.style.display = 'block';
                video.style.display = 'none';

                takeBtn.style.display = 'none';
                retryBtn.style.display = 'block';
                confirmBtn.style.display = 'block';

                if (isFirstEnrollment && warning) {
                    warning.style.display = 'block';
                }
            };

            retryBtn.onclick = () => {
                selectedImageBase64 = null;
                preview.style.display = 'none';
                video.style.display = 'block';
                takeBtn.style.display = 'block';
                retryBtn.style.display = 'none';
                confirmBtn.style.display = 'none';
                if (warning) {
                    warning.style.display = 'none';
                }
            };

            confirmBtn.onclick = () => {
                if (!selectedImageBase64) {
                    reject(new Error('Tire uma foto antes de confirmar'));
                    return;
                }
                cleanup();
                resolve(selectedImageBase64);
            };
        } catch (error) {
            cleanup();
            reject(error);
        }
    });
}

async function runFaceIdentityGate(userId) {
    showLoading('A verificar estado de identidade facial...');
    let status = null;

    try {
        status = await getFaceIdentityStatus(userId);
    } finally {
        hideLoading();
    }

    if (!status.available) {
        throw new Error(status.detail || 'Face identity service is unavailable');
    }

    let consentToStore = false;
    if (!status.enrolled) {
        consentToStore = window.confirm(
            'Antes da primeira transacao precisamos guardar uma selfie mestre na base de dados para comparacao nas proximas transacoes. Ao continuar, voce autoriza este armazenamento para seguranca e prevencao de fraude.'
        );

        if (!consentToStore) {
            throw new Error('Nao e possivel continuar sem aceitar o termo de armazenamento da selfie mestre.');
        }
        const selfieBase64 = await captureFaceSnapshotForIdentity(true);

        showLoading('A guardar selfie mestre (primeira vez pode demorar alguns segundos)...');
        try {
            const { response, data: result } = await fetchJsonWithTimeout(
                `${API_BASE}/api/face-id/verify`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        image_base64: selfieBase64,
                        consent_to_store: consentToStore
                    })
                },
                FACE_VERIFY_TIMEOUT_MS
            );

            if (!response.ok) {
                throw new Error(result.detail || 'Face enrollment failed');
            }

            if (result.mode === 'enroll') {
                showSuccess('Selfie mestre guardada com sucesso.');
                await loadFaceProfileBanner();
            }

            return result;
        } finally {
            hideLoading();
        }
    }

    // From second transaction onward, comparison is performed in liveness modal webcam.
    return { success: true, mode: 'enrolled' };
}

async function devResetFaceIdentity() {
    if (!currentUser?._id) {
        throw new Error('No active user for face reset');
    }

    const { response, data } = await fetchJsonWithTimeout(
        `${API_BASE}/api/face-id/reset/${currentUser._id}`,
        { method: 'POST' },
        15000
    );

    if (!response.ok) {
        throw new Error(data.detail || 'Could not reset face identity');
    }

    await loadFaceProfileBanner();
    return data;
}

window.devResetFaceIdentity = devResetFaceIdentity;

// Handle send money
async function handleSendMoney(event) {
    event.preventDefault();

    if (isSendingMoney) {
        return;
    }
    isSendingMoney = true;
    
    const recipientEmail = document.getElementById('recipient-select').value;
    const cardIndex = parseInt(document.getElementById('card-select').value);
    const amount = parseFloat(document.getElementById('amount-input').value);
    const locationKey = document.getElementById('location-select').value;
    
    const recipient = contacts.find(c => c.email === recipientEmail);
    if (!recipient) {
        showError('Invalid contact');
        isSendingMoney = false;
        return;
    }
    
    // Validate card selection
    if (isNaN(cardIndex) || !userCards[cardIndex]) {
        showError('Please select a card');
        isSendingMoney = false;
        return;
    }
    
    const selectedCard = userCards[cardIndex];
    
    // Validate card balance
    if (selectedCard.balance < amount) {
        showError(`Insufficient balance. Available: €${selectedCard.balance.toFixed(2)}`);
        isSendingMoney = false;
        return;
    }
    
    let location = LOCATIONS[locationKey];
    if (locationKey === 'realtime') {
        try {
            location = await resolveRealtimeLocation();
        } catch (error) {
            console.warn('Realtime location unavailable, falling back to home location', error);
            location = LOCATIONS.home;
            showError('Could not get real GPS location. Falling back to Home location.');
        }
    }

    // Mandatory face identity gate before transaction and liveness flow
    try {
        await runFaceIdentityGate(currentUser._id);
    } catch (error) {
        showError(error.message || 'Face identity verification failed');
        isSendingMoney = false;
        return;
    }
    
    // Create transaction
    showLoading('Creating transaction...');
    
    try {
        const { response, data: transaction } = await fetchJsonWithTimeout(
            `${API_BASE}/api/transactions/`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: currentUser._id,
                    card_index: cardIndex,  // Send card index instead of card_id
                    amount: amount,
                    type: 'transfer',
                    recipient_email: recipientEmail,
                    user_location: location
                })
            },
            CREATE_TX_TIMEOUT_MS
        );
        
        if (!response.ok) {
            throw new Error(transaction.detail || 'Error creating transaction');
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
            showSuccess(`Transaction of €${amount.toFixed(2)} sent to ${recipient.name}!`);
            await loadUserData();
            await loadCards();  // Reload cards to update balances
            await loadTransactions();
            
            // Clear form
            document.getElementById('send-money-form').reset();
        }
    } catch (error) {
        console.error('Transaction error:', error);
        hideLoading();
        showError(error.message);
    } finally {
        isSendingMoney = false;
    }
}

// Show liveness verification
function showLivenessVerification(transaction) {
    if (typeof startLivenessVerification !== 'function') {
        showError('Webcam module not loaded. Refresh the page and try again.');
        return;
    }

    window.onLivenessCompleted = async (result) => {
        if (result.success) {
            showSuccess(`
                <div class="text-center">
                    <div class="text-6xl mb-4">✅</div>
                    <h3 class="text-2xl font-bold mb-2">Verification Complete!</h3>
                    <p class="text-gray-600">Transaction approved successfully</p>
                </div>
            `);
        } else {
            const backendMessage = result.message || 'Could not validate liveness.';
            const normalizedMessage = backendMessage.toLowerCase();
            const displayMessage = normalizedMessage.includes('face lost for more than')
                ? 'Rosto ausente durante mais de 5 segundos. A transacao foi cancelada por seguranca.'
                : backendMessage;

            showError(`
                <div class="text-center">
                    <div class="text-6xl mb-4">❌</div>
                    <h3 class="text-2xl font-bold mb-2">Verification Failed</h3>
                    <p class="text-gray-600">${displayMessage}</p>
                </div>
            `);

            if (result.transaction) {
                showRiskExplainModal(result.transaction);
            }
        }

        await loadUserData();
        await loadCards();
        await loadTransactions();
    };

    startLivenessVerification(transaction._id, currentUser._id);
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
    
    showLoading('Adding card...');
    
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
            showSuccess('Card added successfully!');
            await loadCards();
            
            // Clear form
            event.target.reset();
        } else {
            throw new Error(data.detail || 'Error adding card');
        }
    } catch (error) {
        hideLoading();
        showError(error.message);
        console.error('Add card error:', error);
    }
}

// Delete card
async function deleteCard(cardIndex) {
    if (!confirm('Are you sure you want to remove this card?')) {
        return;
    }
    
    showLoading('Removing card...');
    
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser._id}/cards/${cardIndex}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            hideLoading();
            showSuccess('Card removed successfully!');
            await loadCards();
        } else {
            throw new Error(data.detail || 'Error removing card');
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
    TokenManager.logout();
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

function showLoading(message = 'Loading...') {
    document.querySelectorAll('#loading-modal').forEach((modal) => modal.remove());

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
    document.querySelectorAll('#loading-modal').forEach((modal) => {
        modal.style.opacity = '0';
        setTimeout(() => modal.remove(), 200);
    });
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


