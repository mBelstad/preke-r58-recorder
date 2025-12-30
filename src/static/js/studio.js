/**
 * R58 Studio Section
 * Multiview, Recording Controls, and Camera Management
 */

// Studio state
const studioState = {
    recordingState: false,
    recordingStartTime: null,
    recordingInterval: null,
    fullscreenCamera: null,
    hlsPlayers: {},
    webrtcConnections: {},
    cameraStreamStates: {},
    streamMode: localStorage.getItem('streamMode') || 'balanced',
    isRemote: window.location.hostname.includes('itagenten.no')
};

// API configuration
const API_BASE = window.location.origin;
const HOSTNAME = window.location.hostname;

// Get streaming URLs
function getWebRTCUrl(streamPath) {
    // Always use the proxy endpoint (handles HTTPS/TLS internally)
    // Direct MediaMTX access causes CORS issues
    return `${API_BASE}/${streamPath}/whep`;
}

function getHLSUrl(streamPath) {
    if (studioState.isRemote) {
        return `${API_BASE}/hls/${streamPath}/index.m3u8`;
    } else {
        return `http://${HOSTNAME}:8888/${streamPath}/index.m3u8`;
    }
}

// Load Studio Content
async function loadStudioContent(container) {
    container.innerHTML = `
        <style>
            .studio-layout {
                display: grid;
                grid-template-columns: 1fr 320px;
                gap: var(--spacing-lg);
                height: 100%;
            }

            .studio-main {
                display: flex;
                flex-direction: column;
                gap: var(--spacing-md);
                min-height: 0;
            }

            .multiview-container {
                flex: 1;
                background: var(--bg-primary);
                border-radius: var(--radius-lg);
                overflow: hidden;
                display: grid;
                grid-template-columns: 1fr 1fr;
                grid-template-rows: 1fr 1fr;
                gap: 8px;
                padding: 8px;
                box-shadow: var(--shadow-md);
            }

            .multiview-container.fullscreen {
                grid-template-columns: 1fr;
                grid-template-rows: 1fr;
            }

            .camera-view {
                position: relative;
                background: #000;
                border-radius: var(--radius-md);
                overflow: hidden;
                cursor: pointer;
                transition: all var(--transition-fast);
            }

            .camera-view:hover {
                transform: scale(1.02);
                box-shadow: var(--shadow-lg);
            }

            .camera-view.fullscreen {
                transform: none;
            }

            .camera-view video {
                width: 100%;
                height: 100%;
                object-fit: contain;
                display: block;
            }

            .camera-label {
                position: absolute;
                top: 12px;
                left: 12px;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(8px);
                color: white;
                padding: 6px 12px;
                border-radius: var(--radius-sm);
                font-size: var(--text-sm);
                font-weight: var(--weight-semibold);
                z-index: 10;
            }

            .camera-info {
                position: absolute;
                bottom: 12px;
                left: 12px;
                right: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 10;
            }

            .camera-resolution {
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(8px);
                color: var(--success);
                padding: 4px 10px;
                border-radius: var(--radius-sm);
                font-size: var(--text-xs);
                font-weight: var(--weight-medium);
                font-family: var(--font-mono);
            }

            .camera-signal {
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(8px);
                color: white;
                padding: 4px 10px;
                border-radius: var(--radius-sm);
                font-size: var(--text-xs);
                font-weight: var(--weight-medium);
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .signal-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: var(--text-tertiary);
            }

            .signal-dot.live {
                background: var(--success);
                animation: pulse 2s infinite;
            }

            .camera-placeholder {
                position: absolute;
                inset: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background: rgba(0, 0, 0, 0.9);
                color: var(--text-tertiary);
                gap: var(--spacing-sm);
                z-index: 5;
            }

            .camera-placeholder.hidden {
                display: none;
            }

            .camera-close {
                position: absolute;
                top: 12px;
                right: 12px;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(8px);
                color: white;
                padding: 6px 12px;
                border-radius: var(--radius-sm);
                font-size: var(--text-sm);
                font-weight: var(--weight-semibold);
                cursor: pointer;
                opacity: 0;
                transition: opacity var(--transition-fast);
                z-index: 15;
            }

            .camera-view.fullscreen .camera-close {
                opacity: 1;
            }

            .studio-sidebar {
                display: flex;
                flex-direction: column;
                gap: var(--spacing-md);
                overflow-y: auto;
            }

            .control-card {
                background: var(--bg-primary);
                border-radius: var(--radius-lg);
                padding: var(--spacing-lg);
                box-shadow: var(--shadow-sm);
            }

            .control-card h3 {
                font-size: var(--text-lg);
                margin-bottom: var(--spacing-md);
                color: var(--text-primary);
            }

            .recording-status {
                display: inline-flex;
                align-items: center;
                gap: var(--spacing-sm);
                padding: 8px 16px;
                border-radius: var(--radius-full);
                font-size: var(--text-sm);
                font-weight: var(--weight-semibold);
                margin-bottom: var(--spacing-md);
            }

            .recording-status.idle {
                background: var(--bg-tertiary);
                color: var(--text-secondary);
            }

            .recording-status.recording {
                background: var(--danger-light);
                color: var(--danger);
            }

            .stat-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: var(--spacing-sm);
                margin-top: var(--spacing-md);
            }

            .stat-item {
                background: var(--bg-secondary);
                padding: var(--spacing-md);
                border-radius: var(--radius-md);
            }

            .stat-label {
                font-size: var(--text-xs);
                color: var(--text-secondary);
                margin-bottom: var(--spacing-xs);
            }

            .stat-value {
                font-size: var(--text-lg);
                font-weight: var(--weight-semibold);
                color: var(--text-primary);
            }

            .camera-list-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: var(--spacing-sm) 0;
                border-bottom: 1px solid var(--border);
            }

            .camera-list-item:last-child {
                border-bottom: none;
            }

            @media (max-width: 1024px) {
                .studio-layout {
                    grid-template-columns: 1fr;
                }

                .studio-sidebar {
                    order: -1;
                }

                .multiview-container {
                    min-height: 400px;
                }
            }
        </style>

        <div class="studio-layout">
            <div class="studio-main">
                <div class="multiview-container" id="multiview"></div>
            </div>

            <div class="studio-sidebar">
                <div class="control-card">
                    <h3>Recording</h3>
                    <span class="recording-status idle" id="recordingStatus">IDLE</span>
                    <button class="btn btn-danger w-full" id="recordBtn" onclick="toggleRecording()">
                        <span id="recordBtnText">⏺ Start Recording</span>
                    </button>
                </div>

                <div class="control-card">
                    <h3>Statistics</h3>
                    <div class="stat-grid">
                        <div class="stat-item">
                            <div class="stat-label">Duration</div>
                            <div class="stat-value" id="recordingDuration">00:00:00</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Cameras</div>
                            <div class="stat-value" id="activeCameras">0 / 4</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Session ID</div>
                            <div class="stat-value text-sm" id="sessionId">-</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Disk Space</div>
                            <div class="stat-value" id="diskSpace">-</div>
                        </div>
                    </div>
                </div>

                <div class="control-card">
                    <h3>Stream Mode</h3>
                    <select class="input" id="streamModeSelect" onchange="changeStreamMode(this.value)">
                        <option value="lowlatency">Low Latency (~1s)</option>
                        <option value="balanced" selected>Balanced (~2s)</option>
                        <option value="stable">Stable (~10s)</option>
                    </select>
                    <p class="text-secondary text-sm mt-sm" id="modeHint">Balanced mode for most connections</p>
                </div>

                <div class="control-card">
                    <h3>Cameras</h3>
                    <div id="cameraList"></div>
                </div>
            </div>
        </div>
    `;

    // Initialize
    await initializeStudio();
}

// Initialize Studio
async function initializeStudio() {
    try {
        const response = await fetch(`/status`);
        const data = await response.json();
        const multiview = document.getElementById('multiview');
        
        if (!multiview) return;
        
        multiview.innerHTML = '';

        for (const [camId, camData] of Object.entries(data.cameras)) {
            const camNumber = parseInt(camId.replace('cam', '')) + 1;
            const view = document.createElement('div');
            view.className = 'camera-view';
            view.id = `view-${camId}`;
            view.onclick = () => expandCamera(camId);
            
            view.innerHTML = `
                <div class="camera-label">CAM ${camNumber}</div>
                <div class="camera-close" onclick="event.stopPropagation(); closeFullscreen()">[X] Close</div>
                <video id="video-${camId}" autoplay muted playsinline></video>
                <div class="camera-placeholder" id="placeholder-${camId}">
                    <div style="font-size: 48px;">📹</div>
                    <div>Loading preview...</div>
                </div>
                <div class="camera-info">
                    <div class="camera-resolution" id="resolution-${camId}">--</div>
                    <div class="camera-signal" id="signal-${camId}">
                        <span class="signal-dot"></span>
                        <span>IDLE</span>
                    </div>
                </div>
            `;
            multiview.appendChild(view);
        }

        // Start camera previews with delay
        setTimeout(() => startPreviews(), 3000);

        // Update stats (every 15s to reduce CPU load)
        updateStats();
        setInterval(updateStats, 15000);

        // Restore stream mode
        const modeSelect = document.getElementById('streamModeSelect');
        if (modeSelect) {
            modeSelect.value = studioState.streamMode;
        }

    } catch (error) {
        console.error('Failed to initialize studio:', error);
    }
}

// Start camera previews
async function startPreviews() {
    const cameras = ['cam0', 'cam1', 'cam2', 'cam3'];
    
    for (const camId of cameras) {
        const video = document.getElementById(`video-${camId}`);
        if (!video) continue;

        const streamPath = camId;
        
        // Try WHEP first, fall back to HLS
        if (window.RTCPeerConnection) {
            const webrtcUrl = getWebRTCUrl(streamPath);
            startWebRTCPreview(video, webrtcUrl, camId);
        } else {
            startHLSPreview(video, camId, streamPath);
        }
    }
}

// WebRTC preview (placeholder - simplified version)
async function startWebRTCPreview(video, url, camId) {
    try {
        const pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });

        pc.addTransceiver('video', { direction: 'recvonly' });
        pc.addTransceiver('audio', { direction: 'recvonly' });

        pc.ontrack = (event) => {
            video.srcObject = event.streams[0];
            hidePlaceholder(camId);
            updateSignal(camId, 'LIVE', true);
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/sdp' },
            body: pc.localDescription.sdp
        });

        if (response.ok) {
            const answerSDP = await response.text();
            await pc.setRemoteDescription({ type: 'answer', sdp: answerSDP });
            studioState.webrtcConnections[camId] = pc;
        } else {
            // Fall back to HLS
            startHLSPreview(video, camId, camId);
        }
    } catch (error) {
        console.warn(`WebRTC failed for ${camId}, falling back to HLS:`, error);
        startHLSPreview(video, camId, camId);
    }
}

// HLS preview (placeholder - simplified version)
function startHLSPreview(video, camId, streamPath) {
    if (!Hls.isSupported()) return;

    const hls = new Hls();
    const url = getHLSUrl(streamPath);
    
    hls.loadSource(url);
    hls.attachMedia(video);

    hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
        hidePlaceholder(camId);
        updateSignal(camId, 'LIVE', true);
    });

    hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
            updateSignal(camId, 'NO SIGNAL', false);
        }
    });

    studioState.hlsPlayers[camId] = hls;
}

// UI helpers
function hidePlaceholder(camId) {
    const placeholder = document.getElementById(`placeholder-${camId}`);
    if (placeholder) placeholder.classList.add('hidden');
}

function updateSignal(camId, text, isLive) {
    const signal = document.getElementById(`signal-${camId}`);
    if (!signal) return;
    
    const dot = signal.querySelector('.signal-dot');
    const textSpan = signal.querySelector('span:last-child');
    
    if (dot) dot.classList.toggle('live', isLive);
    if (textSpan) textSpan.textContent = text;
}

// Fullscreen toggle
function expandCamera(camId) {
    if (studioState.fullscreenCamera === camId) {
        closeFullscreen();
        return;
    }

    studioState.fullscreenCamera = camId;
    const view = document.getElementById(`view-${camId}`);
    const multiview = document.getElementById('multiview');
    
    document.querySelectorAll('.camera-view').forEach(v => {
        if (v.id !== `view-${camId}`) {
            v.style.display = 'none';
        }
    });
    
    view.classList.add('fullscreen');
    multiview.classList.add('fullscreen');
}

function closeFullscreen() {
    if (!studioState.fullscreenCamera) return;
    
    const view = document.getElementById(`view-${studioState.fullscreenCamera}`);
    const multiview = document.getElementById('multiview');
    
    view.classList.remove('fullscreen');
    multiview.classList.remove('fullscreen');
    
    document.querySelectorAll('.camera-view').forEach(v => {
        v.style.display = 'block';
    });
    
    studioState.fullscreenCamera = null;
}

// Recording controls
async function toggleRecording() {
    if (studioState.recordingState) {
        await stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const response = await fetch(`${API_BASE}/record/start-all`, { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'recording') {
            studioState.recordingState = true;
            studioState.recordingStartTime = Date.now();
            
            const statusEl = document.getElementById('recordingStatus');
            const btnText = document.getElementById('recordBtnText');
            
            if (statusEl) {
                statusEl.textContent = 'RECORDING';
                statusEl.className = 'recording-status recording';
            }
            if (btnText) btnText.textContent = '⏹ Stop Recording';
            
            startRecordingTimer();
        }
    } catch (error) {
        console.error('Failed to start recording:', error);
    }
}

async function stopRecording() {
    try {
        await fetch(`${API_BASE}/record/stop-all`, { method: 'POST' });
        
        studioState.recordingState = false;
        studioState.recordingStartTime = null;
        
        const statusEl = document.getElementById('recordingStatus');
        const btnText = document.getElementById('recordBtnText');
        const durationEl = document.getElementById('recordingDuration');
        
        if (statusEl) {
            statusEl.textContent = 'IDLE';
            statusEl.className = 'recording-status idle';
        }
        if (btnText) btnText.textContent = '⏺ Start Recording';
        if (durationEl) durationEl.textContent = '00:00:00';
        
        if (studioState.recordingInterval) {
            clearInterval(studioState.recordingInterval);
        }
    } catch (error) {
        console.error('Failed to stop recording:', error);
    }
}

function startRecordingTimer() {
    studioState.recordingInterval = setInterval(() => {
        if (!studioState.recordingStartTime) return;
        
        const elapsed = Date.now() - studioState.recordingStartTime;
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        
        const durationEl = document.getElementById('recordingDuration');
        if (durationEl) {
            durationEl.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    }, 1000);
}

// Update stats
async function updateStats() {
    try {
        const response = await fetch(`/status`);
        const data = await response.json();
        
        const diskSpaceEl = document.getElementById('diskSpace');
        if (diskSpaceEl && data.disk_space) {
            diskSpaceEl.textContent = data.disk_space;
        }
        
        const activeCamsEl = document.getElementById('activeCameras');
        if (activeCamsEl && data.cameras) {
            const activeCount = Object.values(data.cameras).filter(c => c.signal_detected).length;
            activeCamsEl.textContent = `${activeCount} / ${Object.keys(data.cameras).length}`;
        }

        const cameraListEl = document.getElementById('cameraList');
        if (cameraListEl && data.cameras) {
            cameraListEl.innerHTML = Object.entries(data.cameras).map(([camId, camData]) => {
                const camNumber = parseInt(camId.replace('cam', '')) + 1;
                const status = camData.signal_detected ? 'READY' : 'DISCONNECTED';
                const badgeClass = camData.signal_detected ? 'badge-success' : 'badge-neutral';
                return `
                    <div class="camera-list-item">
                        <span>CAM ${camNumber}</span>
                        <span class="badge ${badgeClass}">${status}</span>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.warn('Failed to update stats:', error);
    }
}

// Stream mode change
function changeStreamMode(mode) {
    studioState.streamMode = mode;
    localStorage.setItem('streamMode', mode);
    
    const hints = {
        'lowlatency': 'Ultra-low latency for local viewing (~1s delay)',
        'balanced': 'Balanced mode for most connections (~2s delay)',
        'stable': 'Most stable for bad connections (~10s delay, large buffer)'
    };
    
    const hintEl = document.getElementById('modeHint');
    if (hintEl) {
        hintEl.textContent = hints[mode] || '';
    }
}

// Make functions available globally
window.loadStudioContent = loadStudioContent;
window.toggleRecording = toggleRecording;
window.changeStreamMode = changeStreamMode;
window.expandCamera = expandCamera;
window.closeFullscreen = closeFullscreen;

