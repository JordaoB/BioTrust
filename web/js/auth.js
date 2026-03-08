/**
 * BioTrust Auth - Sistema de Autenticação
 * v1.0 - MBWay Style Interface
 */

const API_BASE = '';

// Toggle between login and register forms
function showRegisterForm() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
}

function showLoginForm() {
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
}

// Handle Login
async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Save session token
            localStorage.setItem('session_token', data.session_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            
            // Success animation
            showSuccessMessage('Login bem-sucedido!');
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/static/dashboard.html';
            }, 1000);
        } else {
            showErrorMessage(data.message || 'Email ou password incorreto');
        }
    } catch (error) {
        console.error('Login error:', error);
        showErrorMessage('Erro de conexão. Tente novamente.');
    }
}

// Handle Register
async function handleRegister(event) {
    event.preventDefault();
    
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const phone = document.getElementById('register-phone').value;
    const password = document.getElementById('register-password').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, email, phone, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Save session token
            localStorage.setItem('session_token', data.session_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            
            // Success animation
            showSuccessMessage('Conta criada com sucesso! Redirecionando...');
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/static/dashboard.html';
            }, 1500);
        } else {
            showErrorMessage(data.detail || 'Erro ao criar conta');
        }
    } catch (error) {
        console.error('Register error:', error);
        showErrorMessage('Erro de conexão. Tente novamente.');
    }
}

// Show success message
function showSuccessMessage(message) {
    const alert = document.createElement('div');
    alert.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-4 rounded-xl shadow-lg z-50 animate-slide-in';
    alert.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-check-circle text-xl mr-3"></i>
            <span>${message}</span>
        </div>
    `;
    document.body.appendChild(alert);
    
    setTimeout(() => {
        alert.classList.add('animate-slide-out');
        setTimeout(() => alert.remove(), 300);
    }, 3000);
}

// Show error message
function showErrorMessage(message) {
    const alert = document.createElement('div');
    alert.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-4 rounded-xl shadow-lg z-50 animate-slide-in';
    alert.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-exclamation-circle text-xl mr-3"></i>
            <span>${message}</span>
        </div>
    `;
    document.body.appendChild(alert);
    
    setTimeout(() => {
        alert.classList.add('animate-slide-out');
        setTimeout(() => alert.remove(), 300);
    }, 4000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slide-in {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slide-out {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    .animate-slide-in {
        animation: slide-in 0.3s ease-out;
    }
    
    .animate-slide-out {
        animation: slide-out 0.3s ease-in;
    }
`;
document.head.appendChild(style);

// Check if already logged in
window.addEventListener('DOMContentLoaded', () => {
    const sessionToken = localStorage.getItem('session_token');
    if (sessionToken && window.location.pathname === '/web') {
        // Verify session is still valid
        fetch(`${API_BASE}/api/auth/session/${sessionToken}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/static/dashboard.html';
                }
            })
            .catch(() => {
                // Session invalid, clear and stay on login
                localStorage.clear();
            });
    }
});
