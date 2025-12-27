/**
 * R58 Guests Section
 * Guest Management and Invite Links
 */

function loadGuestsContent(container) {
    container.innerHTML = `
        <style>
            .guests-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: var(--spacing-lg);
                margin-bottom: var(--spacing-xl);
            }

            .invite-card {
                background: var(--bg-primary);
                border-radius: var(--radius-lg);
                padding: var(--spacing-lg);
                box-shadow: var(--shadow-md);
            }

            .invite-card h3 {
                font-size: var(--text-xl);
                margin-bottom: var(--spacing-sm);
            }

            .invite-card p {
                color: var(--text-secondary);
                margin-bottom: var(--spacing-md);
                font-size: var(--text-sm);
            }

            .invite-link {
                background: var(--bg-secondary);
                padding: var(--spacing-md);
                border-radius: var(--radius-md);
                margin-bottom: var(--spacing-md);
                word-break: break-all;
            }

            .invite-url {
                font-family: var(--font-mono);
                font-size: var(--text-sm);
                color: var(--accent);
            }

            .guest-slots {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: var(--spacing-md);
                margin-top: var(--spacing-xl);
            }

            .guest-slot {
                background: var(--bg-primary);
                border: 2px dashed var(--border);
                border-radius: var(--radius-lg);
                padding: var(--spacing-lg);
                text-align: center;
                min-height: 200px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                transition: all var(--transition-fast);
            }

            .guest-slot.occupied {
                border-style: solid;
                border-color: var(--accent);
                background: var(--accent-light);
            }

            .guest-slot-empty {
                color: var(--text-tertiary);
                font-size: var(--text-sm);
            }

            .guest-preview {
                width: 100%;
                aspect-ratio: 16/9;
                background: #000;
                border-radius: var(--radius-md);
                margin-bottom: var(--spacing-sm);
            }

            .guest-name {
                font-weight: var(--weight-semibold);
                margin-bottom: var(--spacing-sm);
            }

            .guest-controls {
                display: flex;
                gap: var(--spacing-sm);
                margin-top: var(--spacing-sm);
            }
        </style>

        <div class="guests-grid">
            <div class="invite-card">
                <h3>🎤 Invite Guest</h3>
                <p>Share this link for guests to join with camera and microphone</p>
                <div class="invite-link">
                    <div class="invite-url" id="guestInviteLink">Loading...</div>
                </div>
                <div class="flex gap-sm">
                    <button class="btn btn-primary flex-1" onclick="copyGuestLink()">
                        📋 Copy Link
                    </button>
                    <button class="btn btn-secondary" onclick="openGuestPortal()">
                        🔗 Open
                    </button>
                </div>
            </div>

            <div class="invite-card">
                <h3>🎬 VDO.ninja Director</h3>
                <p>Full control room for managing all guests and cameras</p>
                <div class="invite-link">
                    <div class="invite-url" id="directorLink">https://r58-vdo.itagenten.no/?director=r58studio</div>
                </div>
                <div class="flex gap-sm">
                    <button class="btn btn-primary flex-1" onclick="copyDirectorLink()">
                        📋 Copy Link
                    </button>
                    <button class="btn btn-secondary" onclick="openDirectorRoom()">
                        🔗 Open
                    </button>
                </div>
            </div>

            <div class="invite-card">
                <h3>🎛️ Full Mixer</h3>
                <p>VDO.ninja mixer with all active cameras and speakers</p>
                <div class="invite-link">
                    <div class="invite-url text-xs" id="mixerLinkPreview">Loading mixer URL...</div>
                </div>
                <button class="btn btn-primary w-full" onclick="openMixerFromGuests()">
                    🔗 Open Mixer
                </button>
            </div>
        </div>

        <div>
            <h2 class="mb-md">Active Guest Slots</h2>
            <div class="guest-slots" id="guestSlots">
                <div class="guest-slot" data-slot="0">
                    <div class="guest-slot-empty">
                        <div style="font-size: 48px; margin-bottom: var(--spacing-sm);">👤</div>
                        <div>Guest Slot 1</div>
                        <div class="text-xs">Empty</div>
                    </div>
                </div>
                <div class="guest-slot" data-slot="1">
                    <div class="guest-slot-empty">
                        <div style="font-size: 48px; margin-bottom: var(--spacing-sm);">👤</div>
                        <div>Guest Slot 2</div>
                        <div class="text-xs">Empty</div>
                    </div>
                </div>
                <div class="guest-slot" data-slot="2">
                    <div class="guest-slot-empty">
                        <div style="font-size: 48px; margin-bottom: var(--spacing-sm);">👤</div>
                        <div>Guest Slot 3</div>
                        <div class="text-xs">Empty</div>
                    </div>
                </div>
                <div class="guest-slot" data-slot="3">
                    <div class="guest-slot-empty">
                        <div style="font-size: 48px; margin-bottom: var(--spacing-sm);">👤</div>
                        <div>Guest Slot 4</div>
                        <div class="text-xs">Empty</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Initialize
    initializeGuests();
}

async function initializeGuests() {
    // Set guest invite link
    const guestLink = `${window.location.origin}/static/guest`;
    const linkEl = document.getElementById('guestInviteLink');
    if (linkEl) {
        linkEl.textContent = guestLink;
    }

    // Fetch and display VDO.ninja URLs
    await updateVDOninjaLinks();

    // Poll for active guests
    updateGuestSlots();
    setInterval(updateGuestSlots, 5000);
}

async function updateVDOninjaLinks() {
    try {
        // Update director link
        const dirResponse = await fetch('/api/vdoninja/director-url');
        const dirData = await dirResponse.json();
        const dirEl = document.getElementById('directorLink');
        if (dirEl && dirData.url) {
            dirEl.textContent = dirData.url;
        }

        // Update mixer link preview
        const mixResponse = await fetch('/api/vdoninja/mixer-url');
        const mixData = await mixResponse.json();
        const mixEl = document.getElementById('mixerLinkPreview');
        if (mixEl && mixData.url) {
            // Truncate for display
            const shortUrl = mixData.url.length > 60 
                ? mixData.url.substring(0, 60) + '...'
                : mixData.url;
            mixEl.textContent = shortUrl;
        }
    } catch (error) {
        console.warn('Could not fetch VDO.ninja URLs:', error);
    }
}

async function updateGuestSlots() {
    // Placeholder - would connect to VDO.ninja API or local guest management
    // For now, just show empty slots
}

function copyGuestLink() {
    const link = `${window.location.origin}/static/guest`;
    navigator.clipboard.writeText(link).then(() => {
        showToast('Guest link copied!');
    });
}

async function copyDirectorLink() {
    try {
        const response = await fetch('/api/vdoninja/director-url');
        const data = await response.json();
        if (data.url) {
            await navigator.clipboard.writeText(data.url);
            showToast('Director link copied!');
        }
    } catch (error) {
        // Fallback to hardcoded URL
        const link = 'https://r58-vdo.itagenten.no/?director=r58studio';
        navigator.clipboard.writeText(link).then(() => {
            showToast('Director link copied!');
        });
    }
}

function openGuestPortal() {
    window.open('/static/guest', '_blank');
}

async function openDirectorRoom() {
    try {
        const response = await fetch('/api/vdoninja/director-url');
        const data = await response.json();
        if (data.url) {
            window.open(data.url, '_blank');
        } else {
            // Fallback
            window.open('https://r58-vdo.itagenten.no/?director=r58studio', '_blank');
        }
    } catch (error) {
        window.open('https://r58-vdo.itagenten.no/?director=r58studio', '_blank');
    }
}

async function openMixerFromGuests() {
    try {
        const response = await fetch('/api/vdoninja/mixer-url');
        const data = await response.json();
        if (data.url) {
            window.open(data.url, '_blank');
        } else {
            showToast('Failed to generate mixer URL');
        }
    } catch (error) {
        console.error('Failed to open mixer:', error);
        showToast('Error opening mixer');
    }
}

function showToast(message) {
    // Simple toast notification
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
        z-index: var(--z-toast);
        animation: slideInUp var(--transition-base);
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut var(--transition-base)';
        setTimeout(() => toast.remove(), 200);
    }, 2000);
}

// Make functions available globally
window.loadGuestsContent = loadGuestsContent;
window.copyGuestLink = copyGuestLink;
window.copyDirectorLink = copyDirectorLink;
window.openGuestPortal = openGuestPortal;
window.openDirectorRoom = openDirectorRoom;
window.openMixerFromGuests = openMixerFromGuests;

