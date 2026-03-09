/**
 * BioTrust Token Manager
 * Handles access/refresh tokens with automatic renewal
 */

const API_BASE = '';

// Token management utilities
const TokenManager = {
    // Get current access token
    getAccessToken() {
        return localStorage.getItem('access_token');
    },
    
    // Get refresh token
    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },
    
    // Save tokens
    saveTokens(accessToken, refreshToken, expiresAt) {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        localStorage.setItem('access_token_expires_at', expiresAt);
    },
    
    // Clear all tokens
    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('access_token_expires_at');
        localStorage.removeItem('user');
    },
    
    // Check if token needs refresh (within 5 minutes of expiration)
    shouldRefreshToken() {
        const expiresAt = localStorage.getItem('access_token_expires_at');
        if (!expiresAt) return false;
        
        const expiryTime = new Date(expiresAt).getTime();
        const now = new Date().getTime();
        const fiveMinutes = 5 * 60 * 1000;
        
        return (expiryTime - now) < fiveMinutes;
    },
    
    // Check if token is expired
    isTokenExpired() {
        const expiresAt = localStorage.getItem('access_token_expires_at');
        if (!expiresAt) return true;
        
        const expiryTime = new Date(expiresAt).getTime();
        const now = new Date().getTime();
        
        return now >= expiryTime;
    },
    
    // Refresh access token using refresh token
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            console.log('❌ No refresh token available');
            return false;
        }
        
        try {
            const response = await fetch(`${API_BASE}/api/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.saveTokens(
                    data.access_token,
                    data.refresh_token,
                    data.access_token_expires_at
                );
                console.log('✅ Access token refreshed successfully');
                return true;
            } else {
                console.log('❌ Token refresh failed:', response.status);
                return false;
            }
        } catch (error) {
            console.error('Token refresh error:', error);
            return false;
        }
    },
    
    // Make authenticated API request with auto-refresh
    async fetchWithAuth(url, options = {}) {
        // Check if token needs refresh before request
        if (this.shouldRefreshToken()) {
            console.log('🔄 Token expiring soon, refreshing...');
            await this.refreshAccessToken();
        }
        
        // Get current access token
        const accessToken = this.getAccessToken();
        if (!accessToken) {
            throw new Error('No access token available');
        }
        
        // Add authorization header
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${accessToken}`
        };
        
        // Make request
        let response = await fetch(url, { ...options, headers });
        
        // If 401 (unauthorized), try to refresh token once
        if (response.status === 401) {
            console.log('🔄 Got 401, attempting token refresh...');
            const refreshed = await this.refreshAccessToken();
            
            if (refreshed) {
                // Retry request with new token
                const newAccessToken = this.getAccessToken();
                headers['Authorization'] = `Bearer ${newAccessToken}`;
                response = await fetch(url, { ...options, headers });
            } else {
                // Refresh failed, redirect to login
                this.clearTokens();
                window.location.href = '/web';
                throw new Error('Session expired, please login again');
            }
        }
        
        return response;
    },
    
    // Start auto-refresh interval
    startAutoRefresh() {
        // Check every minute
        setInterval(() => {
            if (this.shouldRefreshToken()) {
                console.log('⏰ Auto-refresh triggered');
                this.refreshAccessToken();
            }
        }, 60000); // 1 minute
        
        console.log('✅ Token auto-refresh activated');
    },
    
    // Logout
    async logout() {
        const accessToken = this.getAccessToken();
        
        if (accessToken) {
            try {
                await fetch(`${API_BASE}/api/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ access_token: accessToken })
                });
            } catch (error) {
                console.error('Logout error:', error);
            }
        }
        
        this.clearTokens();
        window.location.href = '/web';
    }
};

// Start auto-refresh when page loads
if (TokenManager.getAccessToken()) {
    TokenManager.startAutoRefresh();
}
