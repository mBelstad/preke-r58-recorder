/**
 * TURN Client for R58
 * Fetches TURN credentials from Coolify API
 */

class TURNClient {
    constructor(apiUrl = null) {
        // Auto-detect API URL based on environment
        if (apiUrl) {
            this.apiUrl = apiUrl;
        } else if (window.location.hostname.includes('itagenten.no')) {
            // Remote access via Cloudflare or direct domain
            this.apiUrl = 'https://api.r58.itagenten.no/turn-credentials';
        } else if (window.location.hostname === 'localhost' || window.location.hostname.startsWith('192.168') || window.location.hostname.startsWith('10.')) {
            // Local access - use local R58 API
            this.apiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/turn-credentials`;
        } else {
            // Default to Coolify API
            this.apiUrl = 'https://api.r58.itagenten.no/turn-credentials';
        }
        
        this.cachedCredentials = null;
        this.cacheExpiry = null;
        
        console.log(`[TURN Client] Using API: ${this.apiUrl}`);
    }
    
    /**
     * Get TURN credentials (with caching)
     * @returns {Promise<Object>} ICE servers configuration
     */
    async getCredentials() {
        // Check cache
        if (this.cachedCredentials && this.cacheExpiry && Date.now() < this.cacheExpiry) {
            console.log('[TURN Client] Using cached credentials');
            return this.cachedCredentials;
        }
        
        try {
            console.log('[TURN Client] Fetching fresh credentials...');
            const response = await fetch(this.apiUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (!data.iceServers || !Array.isArray(data.iceServers)) {
                throw new Error('Invalid response format');
            }
            
            // Cache credentials (expire 1 hour before actual expiry for safety)
            this.cachedCredentials = data.iceServers;
            if (data.expiresAt) {
                this.cacheExpiry = new Date(data.expiresAt).getTime() - (60 * 60 * 1000); // 1 hour buffer
            } else {
                this.cacheExpiry = Date.now() + (23 * 60 * 60 * 1000); // 23 hours
            }
            
            console.log('[TURN Client] ✓ Credentials obtained');
            console.log(`[TURN Client] Cache expires: ${new Date(this.cacheExpiry).toLocaleString()}`);
            
            return this.cachedCredentials;
            
        } catch (error) {
            console.error('[TURN Client] Failed to fetch credentials:', error);
            
            // Return fallback STUN-only configuration
            console.warn('[TURN Client] Using fallback STUN-only configuration');
            return [
                { urls: 'stun:stun.cloudflare.com:3478' },
                { urls: 'stun:stun.l.google.com:19302' }
            ];
        }
    }
    
    /**
     * Get ICE servers for RTCPeerConnection
     * @returns {Promise<Array>} Array of ICE server configurations
     */
    async getIceServers() {
        return await this.getCredentials();
    }
    
    /**
     * Clear cached credentials (force refresh on next request)
     */
    clearCache() {
        this.cachedCredentials = null;
        this.cacheExpiry = null;
        console.log('[TURN Client] Cache cleared');
    }
    
    /**
     * Check if remote access is being used
     * @returns {boolean}
     */
    static isRemoteAccess() {
        const hostname = window.location.hostname;
        return hostname.includes('itagenten.no') || 
               hostname.includes('r58.') ||
               (!hostname.startsWith('192.168') && 
                !hostname.startsWith('10.') && 
                hostname !== 'localhost');
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TURNClient;
}

