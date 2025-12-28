/**
 * R58 Mixer Section
 * VDO.ninja Integration with Camera/Speaker Source Management
 */

// Mixer state
const mixerState = {
    sources: [],
    refreshInterval: null,
    isLoading: false,
    mappings: {},
    hasChanges: false
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

            .mapper-card {
                grid-column: 1 / -1;
            }

            .mapper-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: var(--spacing-md);
            }

            .mapper-item {
                display: flex;
                flex-direction: column;
                gap: var(--spacing-sm);
                padding: var(--spacing-md);
                background: var(--bg-secondary);
                border-radius: var(--radius-md);
                border-left: 4px solid var(--accent);
            }

            .mapper-item.inactive {
                opacity: 0.6;
                border-left-color: var(--text-tertiary);
            }

            .mapper-label {
                font-weight: var(--weight-semibold);
                display: flex;
                align-items: center;
                gap: var(--spacing-sm);
            }

            .mapper-select {
                padding: 8px 12px;
                background: var(--bg-tertiary);
                border: 1px solid var(--border);
                border-radius: var(--radius-md);
                color: var(--text-primary);
                font-size: var(--text-sm);
                cursor: pointer;
            }

            .mapper-select:focus {
                outline: none;
                border-color: var(--accent);
            }

            .mapper-actions {
                display: flex;
                gap: var(--spacing-md);
                margin-top: var(--spacing-md);
            }

            .mapper-actions .btn {
                flex: 1;
            }

            .scene-url-section {
                margin-top: var(--spacing-lg);
                padding-top: var(--spacing-lg);
                border-top: 1px solid var(--border);
            }

            .scene-url-section h4 {
                margin-bottom: var(--spacing-sm);
                display: flex;
                align-items: center;
                gap: var(--spacing-sm);
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
                    <button class="btn action-btn primary" onclick="startStreamingAndOpenMixer()" id="startMixerBtn">
                        🎛️ Start Streaming & Open Mixer
                    </button>
                    <button class="btn action-btn secondary" onclick="openDirector()">
                        🎥 Open Director
                    </button>
                    <button class="btn action-btn secondary" onclick="copyMixerUrl()">
                        📋 Copy Mixer URL
                    </button>
                    <button class="btn action-btn secondary" onclick="startIngestOnly()" id="startIngestBtn">
                        📹 Start Camera Streaming
                    </button>
                </div>
                <div class="url-display" id="mixerUrlDisplay">
                    Loading mixer URL...
                </div>
                
                <div class="scene-url-section">
                    <h4><span>📺</span> Scene View (Program Output)</h4>
                    <div class="url-display" id="sceneUrlDisplay">Loading...</div>
                    <button class="btn action-btn secondary" onclick="copySceneUrl()" style="margin-top: var(--spacing-sm);">
                        📋 Copy Scene URL
                    </button>
                </div>
            </div>

            <div class="mixer-card mapper-card">
                <h3>
                    <span>🔗</span> Camera-to-Slot Mapper
                    <button class="btn btn-ghost refresh-btn" onclick="loadMappings()" title="Reload mappings">🔄</button>
                </h3>
                <p style="color: var(--text-secondary); margin-bottom: var(--spacing-md); font-size: var(--text-sm);">
                    Assign cameras to VDO.ninja mixer slots (0-9). Use "Add Stream ID" in the mixer to add cameras.
                </p>
                <div id="mapperGrid" class="mapper-grid">
                    <div class="loading-spinner">Loading mappings...</div>
                </div>
                <div class="mapper-actions">
                    <button class="btn action-btn primary" onclick="saveMappings()" id="saveMappingsBtn" disabled>
                        💾 Save Mappings
                    </button>
                    <button class="btn action-btn secondary" onclick="resetMappings()">
                        🔄 Reset to Defaults
                    </button>
                </div>
            </div>
        </div>
    `;

    // Initialize
    await initializeMixer();
}

/**
 * Initialize mixer - load sources, mappings and start refresh
 */
async function initializeMixer() {
    await Promise.all([
        refreshSources(),
        loadMappings(),
        loadSceneUrl()
    ]);
    
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
 * Start camera ingest pipelines (stream to MediaMTX)
 */
async function startIngestOnly() {
    const btn = document.getElementById('startIngestBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Starting...';
    }
    
    try {
        const response = await fetch('/api/ingest/start', { method: 'POST' });
        const data = await response.json();
        
        if (data.streaming_count > 0) {
            showMixerToast(`Started streaming ${data.streaming_count} camera(s)`);
        } else {
            showMixerToast('No cameras with signal to start');
        }
        
        // Refresh sources after starting
        await refreshSources();
        
    } catch (error) {
        console.error('Failed to start ingest:', error);
        showMixerToast('Failed to start camera streaming');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = '📹 Start Camera Streaming';
        }
    }
}

/**
 * Start streaming and then open mixer
 */
async function startStreamingAndOpenMixer() {
    const btn = document.getElementById('startMixerBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Starting cameras...';
    }
    
    try {
        // First start the ingest pipelines
        const ingestResponse = await fetch('/api/ingest/start', { method: 'POST' });
        const ingestData = await ingestResponse.json();
        
        if (ingestData.streaming_count > 0) {
            showMixerToast(`Started ${ingestData.streaming_count} camera(s), opening mixer...`);
        }
        
        // Wait a moment for streams to stabilize
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Refresh sources
        await refreshSources();
        
        // Now open the mixer
        const mixerResponse = await fetch('/api/vdoninja/mixer-url');
        const mixerData = await mixerResponse.json();
        
        if (mixerData.url) {
            window.open(mixerData.url, '_blank');
        } else {
            showMixerToast('Failed to generate mixer URL');
        }
        
    } catch (error) {
        console.error('Failed to start streaming and open mixer:', error);
        showMixerToast('Error starting streaming');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🎛️ Start Streaming & Open Mixer';
        }
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

/**
 * Load scene URL
 */
async function loadSceneUrl() {
    try {
        const response = await fetch('/api/vdoninja/scene-url');
        const data = await response.json();
        
        const urlDisplay = document.getElementById('sceneUrlDisplay');
        if (urlDisplay) {
            urlDisplay.textContent = data.url || 'No URL available';
        }
        
        mixerState.sceneUrl = data.url;
    } catch (error) {
        console.error('Failed to load scene URL:', error);
    }
}

/**
 * Copy scene URL to clipboard
 */
async function copySceneUrl() {
    if (mixerState.sceneUrl) {
        await navigator.clipboard.writeText(mixerState.sceneUrl);
        showMixerToast('Scene URL copied! Use in OBS Browser Source.');
    } else {
        showMixerToast('No scene URL available');
    }
}

/**
 * Load camera-to-slot mappings
 */
async function loadMappings() {
    try {
        const response = await fetch('/api/vdoninja/mapping');
        const data = await response.json();
        
        mixerState.mappings = data.raw_mappings || {};
        mixerState.hasChanges = false;
        
        renderMapperGrid();
        updateSaveButton();
        
    } catch (error) {
        console.error('Failed to load mappings:', error);
        document.getElementById('mapperGrid').innerHTML = `
            <div class="mapper-item inactive">
                <span class="mapper-label">Error loading mappings</span>
            </div>
        `;
    }
}

/**
 * Render the mapper grid
 */
function renderMapperGrid() {
    const container = document.getElementById('mapperGrid');
    if (!container) return;
    
    // Define all possible sources
    const allSources = [
        { id: 'cam0', name: 'CAM 1 (HDMI 1)', type: 'camera' },
        { id: 'cam1', name: 'CAM 2 (HDMI 2)', type: 'camera' },
        { id: 'cam2', name: 'CAM 3 (HDMI 3)', type: 'camera' },
        { id: 'cam3', name: 'CAM 4 (HDMI 4)', type: 'camera' },
        { id: 'guest1', name: 'Guest 1', type: 'speaker' },
        { id: 'guest2', name: 'Guest 2', type: 'speaker' },
        { id: 'guest3', name: 'Guest 3', type: 'speaker' },
        { id: 'guest4', name: 'Guest 4', type: 'speaker' }
    ];
    
    // Check which sources are currently active
    const activeSources = new Set(mixerState.sources.filter(s => s.active).map(s => s.stream));
    
    container.innerHTML = allSources.map(source => {
        const isActive = activeSources.has(source.id);
        const currentSlot = mixerState.mappings[source.id] ?? '';
        const icon = source.type === 'camera' ? '📹' : '👤';
        
        // Generate slot options
        const options = ['<option value="">Not mapped</option>'];
        for (let i = 0; i <= 9; i++) {
            const selected = currentSlot === i ? 'selected' : '';
            options.push(`<option value="${i}" ${selected}>Slot ${i}</option>`);
        }
        
        return `
            <div class="mapper-item ${isActive ? '' : 'inactive'}">
                <div class="mapper-label">
                    <span>${icon}</span>
                    <span>${source.name}</span>
                    ${isActive ? '<span style="color: var(--success);">●</span>' : ''}
                </div>
                <select class="mapper-select" data-source="${source.id}" onchange="onMappingChange('${source.id}', this.value)">
                    ${options.join('')}
                </select>
            </div>
        `;
    }).join('');
}

/**
 * Handle mapping change
 */
function onMappingChange(sourceId, value) {
    if (value === '') {
        delete mixerState.mappings[sourceId];
    } else {
        mixerState.mappings[sourceId] = parseInt(value, 10);
    }
    mixerState.hasChanges = true;
    updateSaveButton();
}

/**
 * Update save button state
 */
function updateSaveButton() {
    const btn = document.getElementById('saveMappingsBtn');
    if (btn) {
        btn.disabled = !mixerState.hasChanges;
        btn.textContent = mixerState.hasChanges ? '💾 Save Mappings *' : '💾 Save Mappings';
    }
}

/**
 * Save mappings to server
 */
async function saveMappings() {
    const btn = document.getElementById('saveMappingsBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Saving...';
    }
    
    try {
        const response = await fetch('/api/vdoninja/mapping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mappings: mixerState.mappings })
        });
        
        if (response.ok) {
            mixerState.hasChanges = false;
            showMixerToast('Mappings saved successfully!');
        } else {
            const error = await response.json();
            showMixerToast(`Failed to save: ${error.detail}`);
        }
    } catch (error) {
        console.error('Failed to save mappings:', error);
        showMixerToast('Error saving mappings');
    } finally {
        updateSaveButton();
    }
}

/**
 * Reset mappings to defaults
 */
async function resetMappings() {
    if (!confirm('Reset all mappings to defaults?')) return;
    
    try {
        const response = await fetch('/api/vdoninja/mapping/reset', { method: 'POST' });
        
        if (response.ok) {
            const data = await response.json();
            mixerState.mappings = data.mappings || {};
            mixerState.hasChanges = false;
            renderMapperGrid();
            updateSaveButton();
            showMixerToast('Mappings reset to defaults');
        } else {
            showMixerToast('Failed to reset mappings');
        }
    } catch (error) {
        console.error('Failed to reset mappings:', error);
        showMixerToast('Error resetting mappings');
    }
}

// Make functions available globally
window.loadMixerContent = loadMixerContent;
window.refreshSources = refreshSources;
window.openMixerWithSources = openMixerWithSources;
window.openDirector = openDirector;
window.copyMixerUrl = copyMixerUrl;
window.startIngestOnly = startIngestOnly;
window.startStreamingAndOpenMixer = startStreamingAndOpenMixer;
window.loadMappings = loadMappings;
window.onMappingChange = onMappingChange;
window.saveMappings = saveMappings;
window.resetMappings = resetMappings;
window.copySceneUrl = copySceneUrl;

