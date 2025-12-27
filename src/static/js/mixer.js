/**
 * R58 Mixer Section
 * VDO.ninja Integration with Camera/Speaker Source Management
 */

// Mixer state
const mixerState = {
    sources: [],
    refreshInterval: null,
    isLoading: false
};

/**
 * Load Mixer Content into container
 */
async function loadMixerContent(container) {
    container.innerHTML = `
        <style>
            .mixer-layout {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: var(--spacing-lg);
                max-width: 1200px;
            }

            .mixer-card {
                background: var(--bg-primary);
                border-radius: var(--radius-lg);
                padding: var(--spacing-lg);
                box-shadow: var(--shadow-md);
            }

            .mixer-card h3 {
                font-size: var(--text-xl);
                margin-bottom: var(--spacing-md);
                display: flex;
                align-items: center;
                gap: var(--spacing-sm);
            }

            .source-list {
                display: flex;
                flex-direction: column;
                gap: var(--spacing-sm);
            }

            .source-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: var(--spacing-md);
                background: var(--bg-secondary);
                border-radius: var(--radius-md);
                border-left: 4px solid var(--text-tertiary);
                transition: all var(--transition-fast);
            }

            .source-item.active {
                border-left-color: var(--success);
                background: rgba(52, 199, 89, 0.08);
            }

            .source-item.inactive {
                opacity: 0.6;
            }

            .source-info {
                display: flex;
                align-items: center;
                gap: var(--spacing-md);
            }

            .source-status {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: var(--text-tertiary);
                flex-shrink: 0;
            }

            .source-status.active {
                background: var(--success);
                animation: pulse 2s infinite;
            }

            .source-name {
                font-weight: var(--weight-semibold);
                color: var(--text-primary);
            }

            .source-details {
                font-size: var(--text-sm);
                color: var(--text-secondary);
            }

            .source-type {
                font-size: var(--text-xs);
                padding: 2px 8px;
                border-radius: var(--radius-sm);
                background: var(--bg-tertiary);
                color: var(--text-secondary);
                text-transform: uppercase;
            }

            .source-type.camera {
                background: rgba(0, 122, 255, 0.15);
                color: var(--accent);
            }

            .source-type.speaker {
                background: rgba(255, 149, 0, 0.15);
                color: #FF9500;
            }

            .action-buttons {
                display: flex;
                flex-direction: column;
                gap: var(--spacing-md);
            }

            .action-btn {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: var(--spacing-sm);
                padding: var(--spacing-md) var(--spacing-lg);
                font-size: var(--text-base);
                font-weight: var(--weight-semibold);
            }

            .action-btn.primary {
                background: var(--accent);
                color: white;
            }

            .action-btn.primary:hover {
                background: var(--accent-hover);
            }

            .action-btn.secondary {
                background: var(--bg-secondary);
                border: 1px solid var(--border);
            }

            .action-btn.secondary:hover {
                background: var(--bg-hover);
            }

            .url-display {
                background: var(--bg-secondary);
                border-radius: var(--radius-md);
                padding: var(--spacing-md);
                margin-top: var(--spacing-md);
                word-break: break-all;
                font-family: var(--font-mono);
                font-size: var(--text-xs);
                color: var(--text-secondary);
                max-height: 80px;
                overflow-y: auto;
            }

            .summary-stats {
                display: flex;
                gap: var(--spacing-lg);
                margin-bottom: var(--spacing-lg);
                flex-wrap: wrap;
            }

            .stat-badge {
                display: flex;
                align-items: center;
                gap: var(--spacing-sm);
                padding: var(--spacing-sm) var(--spacing-md);
                background: var(--bg-secondary);
                border-radius: var(--radius-full);
                font-size: var(--text-sm);
            }

            .stat-badge .count {
                font-weight: var(--weight-bold);
                color: var(--accent);
            }

            .loading-spinner {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: var(--spacing-xl);
                color: var(--text-secondary);
            }

            .refresh-btn {
                font-size: var(--text-sm);
                padding: 4px 8px;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            @media (max-width: 768px) {
                .mixer-layout {
                    grid-template-columns: 1fr;
                }
            }
        </style>

        <div class="summary-stats" id="mixerSummary">
            <div class="stat-badge">
                <span>Loading sources...</span>
            </div>
        </div>

        <div class="mixer-layout">
            <div class="mixer-card">
                <h3>
                    <span>📡</span> Active Sources
                    <button class="btn btn-ghost refresh-btn" onclick="refreshSources()" title="Refresh">🔄</button>
                </h3>
                <div id="sourceList" class="source-list">
                    <div class="loading-spinner">Loading sources...</div>
                </div>
            </div>

            <div class="mixer-card">
                <h3><span>🎬</span> VDO.ninja Controls</h3>
                <div class="action-buttons">
                    <button class="btn action-btn primary" onclick="openMixerWithSources()">
                        🎛️ Open Mixer
                    </button>
                    <button class="btn action-btn secondary" onclick="openDirector()">
                        🎥 Open Director
                    </button>
                    <button class="btn action-btn secondary" onclick="copyMixerUrl()">
                        📋 Copy Mixer URL
                    </button>
                </div>
                <div class="url-display" id="mixerUrlDisplay">
                    Loading mixer URL...
                </div>
            </div>
        </div>
    `;

    // Initialize
    await initializeMixer();
}

/**
 * Initialize mixer - load sources and start refresh
 */
async function initializeMixer() {
    await refreshSources();
    
    // Auto-refresh every 5 seconds
    if (mixerState.refreshInterval) {
        clearInterval(mixerState.refreshInterval);
    }
    mixerState.refreshInterval = setInterval(refreshSources, 5000);
}

/**
 * Refresh sources from API
 */
async function refreshSources() {
    if (mixerState.isLoading) return;
    mixerState.isLoading = true;

    try {
        const response = await fetch('/api/vdoninja/sources');
        const data = await response.json();
        
        mixerState.sources = data.sources || [];
        
        renderSources();
        renderSummary(data.summary);
        await updateMixerUrl();
        
    } catch (error) {
        console.error('Failed to fetch sources:', error);
        document.getElementById('sourceList').innerHTML = `
            <div class="source-item inactive">
                <span class="source-info">
                    <span class="source-status"></span>
                    <span class="source-name">Error loading sources</span>
                </span>
            </div>
        `;
    } finally {
        mixerState.isLoading = false;
    }
}

/**
 * Render source list
 */
function renderSources() {
    const container = document.getElementById('sourceList');
    if (!container) return;

    if (mixerState.sources.length === 0) {
        container.innerHTML = `
            <div class="source-item inactive">
                <span class="source-info">
                    <span class="source-status"></span>
                    <span class="source-name">No sources detected</span>
                </span>
            </div>
        `;
        return;
    }

    container.innerHTML = mixerState.sources.map(source => {
        const isActive = source.active;
        const statusClass = isActive ? 'active' : 'inactive';
        const typeClass = source.type;
        const resolutionText = source.resolution || (isActive ? 'Active' : 'No signal');

        return `
            <div class="source-item ${statusClass}">
                <div class="source-info">
                    <span class="source-status ${statusClass}"></span>
                    <div>
                        <div class="source-name">${source.name}</div>
                        <div class="source-details">${source.stream} - ${resolutionText}</div>
                    </div>
                </div>
                <span class="source-type ${typeClass}">${source.type}</span>
            </div>
        `;
    }).join('');
}

/**
 * Render summary stats
 */
function renderSummary(summary) {
    const container = document.getElementById('mixerSummary');
    if (!container || !summary) return;

    container.innerHTML = `
        <div class="stat-badge">
            <span class="count">${summary.active_cameras}</span>
            <span>Active Cameras</span>
        </div>
        <div class="stat-badge">
            <span class="count">${summary.active_speakers}</span>
            <span>Active Speakers</span>
        </div>
        <div class="stat-badge">
            <span class="count">${summary.active}</span>
            <span>Total Sources</span>
        </div>
    `;
}

/**
 * Update mixer URL display
 */
async function updateMixerUrl() {
    try {
        const response = await fetch('/api/vdoninja/mixer-url');
        const data = await response.json();
        
        const urlDisplay = document.getElementById('mixerUrlDisplay');
        if (urlDisplay) {
            urlDisplay.textContent = data.url || 'No URL available';
        }
        
        // Store for copy function
        mixerState.currentMixerUrl = data.url;
        
    } catch (error) {
        console.error('Failed to get mixer URL:', error);
    }
}

/**
 * Open VDO.ninja mixer with all active sources
 */
async function openMixerWithSources() {
    try {
        const response = await fetch('/api/vdoninja/mixer-url');
        const data = await response.json();
        
        if (data.url) {
            window.open(data.url, '_blank');
        } else {
            showMixerToast('Failed to generate mixer URL');
        }
    } catch (error) {
        console.error('Failed to open mixer:', error);
        showMixerToast('Error opening mixer');
    }
}

/**
 * Open VDO.ninja director room
 */
async function openDirector() {
    try {
        const response = await fetch('/api/vdoninja/director-url');
        const data = await response.json();
        
        if (data.url) {
            window.open(data.url, '_blank');
        } else {
            showMixerToast('Failed to generate director URL');
        }
    } catch (error) {
        console.error('Failed to open director:', error);
        showMixerToast('Error opening director');
    }
}

/**
 * Copy mixer URL to clipboard
 */
async function copyMixerUrl() {
    try {
        const response = await fetch('/api/vdoninja/mixer-url');
        const data = await response.json();
        
        if (data.url) {
            await navigator.clipboard.writeText(data.url);
            showMixerToast('Mixer URL copied to clipboard!');
        } else {
            showMixerToast('No URL to copy');
        }
    } catch (error) {
        console.error('Failed to copy URL:', error);
        showMixerToast('Failed to copy URL');
    }
}

/**
 * Show toast notification
 */
function showMixerToast(message) {
    // Use the global showToast if available, otherwise create our own
    if (typeof showToast === 'function') {
        showToast(message);
        return;
    }

    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 12px 20px;
        box-shadow: var(--shadow-lg);
        z-index: 9999;
        animation: slideInUp 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// Make functions available globally
window.loadMixerContent = loadMixerContent;
window.refreshSources = refreshSources;
window.openMixerWithSources = openMixerWithSources;
window.openDirector = openDirector;
window.copyMixerUrl = copyMixerUrl;

