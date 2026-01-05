<script setup lang="ts">
/**
 * Style Guide v2 - Corporate Glassmorphism Design System
 * Based on the DeviceSetupView opening page design
 */
import { ref } from 'vue'

const activeTab = ref('colors')

// Design tokens for display
const colors = {
  brand: [
    { name: 'Gold', var: '--preke-gold', value: '#e0a030' },
    { name: 'Gold Light', var: '--preke-gold-light', value: '#f5c04a' },
    { name: 'Gold Dark', var: '--preke-gold-dark', value: '#c48820' },
  ],
  backgrounds: [
    { name: 'Base', var: '--preke-bg-base', value: '#0a0a0a' },
    { name: 'Elevated', var: '--preke-bg-elevated', value: '#121212' },
    { name: 'Surface', var: '--preke-bg-surface', value: '#1a1a1a' },
  ],
  text: [
    { name: 'Primary', var: '--preke-text-primary', value: '#ffffff' },
    { name: 'Dim', var: '--preke-text-dim', value: '#e8e0d0' },
    { name: 'Muted', var: '--preke-text-muted', value: '#a8a8a8' },
    { name: 'Subtle', var: '--preke-text-subtle', value: '#6a6a6a' },
  ],
  status: [
    { name: 'Blue', var: '--preke-blue', value: '#5a9fd4' },
    { name: 'Green', var: '--preke-green', value: '#6db56d' },
    { name: 'Red', var: '--preke-red', value: '#d45a5a' },
    { name: 'Amber', var: '--preke-amber', value: '#f59e0b' },
  ]
}

const typography = [
  { label: 'XS (11px)', var: '--preke-text-xs', size: '0.6875rem' },
  { label: 'SM (12px)', var: '--preke-text-sm', size: '0.75rem' },
  { label: 'Base (13px)', var: '--preke-text-base', size: '0.8125rem' },
  { label: 'MD (14px)', var: '--preke-text-md', size: '0.875rem' },
  { label: 'LG (15px)', var: '--preke-text-lg', size: '0.9375rem' },
  { label: 'XL (16px)', var: '--preke-text-xl', size: '1rem' },
  { label: '2XL (20px)', var: '--preke-text-2xl', size: '1.25rem' },
  { label: '3XL (24px)', var: '--preke-text-3xl', size: '1.5rem' },
]

// Scanning animation bars
const scanBars = 24
</script>

<template>
  <div class="styleguide-v2">
    <!-- Ambient background orbs -->
    <div class="styleguide-v2__bg">
      <div class="bg-orb bg-orb--1"></div>
      <div class="bg-orb bg-orb--2"></div>
    </div>
    
    <div class="styleguide-v2__content">
      <!-- Header -->
      <header class="styleguide-v2__header">
        <img src="/logo-studio-stacked.svg" alt="Preke Studio" class="header-logo" />
        <div class="header-text">
          <h1>Design System <span class="text-gold">v2.0</span></h1>
          <p>Corporate Glassmorphism — Premium Dark Theme</p>
        </div>
      </header>
      
      <!-- Tab Navigation -->
      <nav class="tabs-nav">
        <button 
          v-for="tab in ['colors', 'typography', 'buttons', 'cards', 'forms', 'components', 'animations']"
          :key="tab"
          :class="['tab-btn', { active: activeTab === tab }]"
          @click="activeTab = tab"
        >
          {{ tab.charAt(0).toUpperCase() + tab.slice(1) }}
        </button>
      </nav>
      
      <!-- Colors Section -->
      <section v-if="activeTab === 'colors'" class="section">
        <div class="section-header">
          <h2>Color Palette</h2>
          <p>Warm gold accents on near-black backgrounds</p>
        </div>
        
        <!-- Brand Colors -->
        <div class="color-group">
          <h3>Brand — Gold Accent</h3>
          <div class="color-grid">
            <div v-for="color in colors.brand" :key="color.var" class="color-swatch">
              <div class="swatch" :style="{ backgroundColor: color.value }"></div>
              <span class="swatch-name">{{ color.name }}</span>
              <code class="swatch-value">{{ color.value }}</code>
              <code class="swatch-var">{{ color.var }}</code>
            </div>
          </div>
        </div>
        
        <!-- Background Colors -->
        <div class="color-group">
          <h3>Backgrounds</h3>
          <div class="color-grid">
            <div v-for="color in colors.backgrounds" :key="color.var" class="color-swatch">
              <div class="swatch" :style="{ backgroundColor: color.value }"></div>
              <span class="swatch-name">{{ color.name }}</span>
              <code class="swatch-value">{{ color.value }}</code>
              <code class="swatch-var">{{ color.var }}</code>
            </div>
          </div>
        </div>
        
        <!-- Text Colors -->
        <div class="color-group">
          <h3>Typography</h3>
          <div class="color-grid">
            <div v-for="color in colors.text" :key="color.var" class="color-swatch">
              <div class="swatch swatch--text" :style="{ backgroundColor: color.value }"></div>
              <span class="swatch-name">{{ color.name }}</span>
              <code class="swatch-value">{{ color.value }}</code>
              <code class="swatch-var">{{ color.var }}</code>
            </div>
          </div>
        </div>
        
        <!-- Status Colors -->
        <div class="color-group">
          <h3>Status Colors</h3>
          <div class="color-grid">
            <div v-for="color in colors.status" :key="color.var" class="color-swatch">
              <div class="swatch" :style="{ backgroundColor: color.value }"></div>
              <span class="swatch-name">{{ color.name }}</span>
              <code class="swatch-value">{{ color.value }}</code>
              <code class="swatch-var">{{ color.var }}</code>
            </div>
          </div>
        </div>
      </section>
      
      <!-- Typography Section -->
      <section v-if="activeTab === 'typography'" class="section">
        <div class="section-header">
          <h2>Typography</h2>
          <p>System fonts with a refined scale</p>
        </div>
        
        <div class="glass-card typography-showcase">
          <div v-for="size in typography" :key="size.var" class="type-row">
            <span class="type-label">{{ size.label }}</span>
            <span class="type-sample" :style="{ fontSize: size.size }">
              The quick brown fox jumps over the lazy dog
            </span>
            <code class="type-var">{{ size.var }}</code>
          </div>
          
          <div class="divider-v2"><span>Weights</span></div>
          
          <div class="weights-row">
            <span style="font-weight: 400">Regular 400</span>
            <span style="font-weight: 500">Medium 500</span>
            <span style="font-weight: 600">Semibold 600</span>
            <span style="font-weight: 700">Bold 700</span>
          </div>
        </div>
      </section>
      
      <!-- Buttons Section -->
      <section v-if="activeTab === 'buttons'" class="section">
        <div class="section-header">
          <h2>Buttons</h2>
          <p>Gradient buttons with 3D depth</p>
        </div>
        
        <div class="glass-card">
          <h3>Primary Actions</h3>
          <div class="button-row">
            <button class="btn-v2 btn-v2--primary">Connect</button>
            <button class="btn-v2 btn-v2--success">Open</button>
            <button class="btn-v2 btn-v2--danger">Disconnect</button>
          </div>
          
          <h3>Secondary Actions</h3>
          <div class="button-row">
            <button class="btn-v2 btn-v2--glass">Settings</button>
            <button class="btn-v2 btn-v2--ghost">
              <svg viewBox="0 0 20 20" fill="currentColor" class="icon-v2">
                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
              </svg>
              Add manually
            </button>
          </div>
          
          <h3>Scan Button with Spinner</h3>
          <div class="button-row">
            <button class="btn-v2 btn-v2--scan">
              <svg viewBox="0 0 20 20" fill="currentColor" class="icon-v2">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"/>
              </svg>
              Scan
            </button>
            <button class="btn-v2 btn-v2--scan spinning">
              <svg viewBox="0 0 20 20" fill="currentColor" class="icon-v2">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"/>
              </svg>
              Searching...
            </button>
            <button class="btn-v2 btn-v2--scan" style="color: var(--preke-red); border-color: rgba(239, 68, 68, 0.3);">
              Stop
            </button>
          </div>
          
          <h3>Icon Buttons</h3>
          <div class="button-row">
            <button class="btn-v2 btn-v2--icon">
              <svg viewBox="0 0 20 20" fill="currentColor" class="icon-v2">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793z"/>
                <path d="M11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
              </svg>
            </button>
            <button class="btn-v2 btn-v2--icon danger">
              <svg viewBox="0 0 20 20" fill="currentColor" class="icon-v2">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"/>
              </svg>
            </button>
          </div>
          
          <h3>Disabled States</h3>
          <div class="button-row">
            <button class="btn-v2 btn-v2--primary" disabled>Disabled</button>
            <button class="btn-v2 btn-v2--glass" disabled>Disabled</button>
          </div>
        </div>
      </section>
      
      <!-- Cards Section -->
      <section v-if="activeTab === 'cards'" class="section">
        <div class="section-header">
          <h2>Glassmorphism Cards</h2>
          <p>Frosted glass effects with 3D depth</p>
        </div>
        
        <div class="cards-grid">
          <div class="glass-card">
            <h3>Glass Card</h3>
            <p>Primary container with blur backdrop, gradient overlays, and multi-layer shadows.</p>
            <div class="button-row">
              <button class="btn-v2 btn-v2--primary">Action</button>
            </div>
          </div>
          
          <div class="glass-panel" style="padding: 1rem;">
            <h3>Glass Panel</h3>
            <p>Lighter variant for list items and nested content.</p>
          </div>
        </div>
        
        <h3 style="margin-top: 2rem;">Device List Items</h3>
        <div class="device-item-v2">
          <div class="icon-box-v2">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <path d="M8 21h8M12 17v4"/>
            </svg>
          </div>
          <div class="device-item-v2__info">
            <span class="device-item-v2__name">Preke Device</span>
            <span class="badge-v2 badge-v2--info">v2.1.0</span>
            <span class="device-item-v2__url">192.168.1.100:8000</span>
          </div>
          <button class="btn-v2 btn-v2--primary">Connect</button>
        </div>
        
        <div class="device-item-v2 device-item-v2--active">
          <div class="icon-box-v2 icon-box-v2--gold">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <path d="M8 21h8M12 17v4"/>
            </svg>
          </div>
          <div class="device-item-v2__info">
            <span class="device-item-v2__name">Studio Pro</span>
            <span class="badge-v2 badge-v2--success">Connected</span>
            <span class="device-item-v2__url">192.168.1.24:8000</span>
          </div>
          <button class="btn-v2 btn-v2--success">Open</button>
          <button class="btn-v2 btn-v2--icon danger">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"/>
            </svg>
          </button>
        </div>
        
        <div class="device-item-v2 device-item-v2--discovered">
          <div class="icon-box-v2 icon-box-v2--green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <path d="M8 21h8M12 17v4"/>
            </svg>
          </div>
          <div class="device-item-v2__info">
            <span class="device-item-v2__name">New Device</span>
            <span class="badge-v2 badge-v2--gold">Found on network</span>
            <span class="device-item-v2__url">192.168.1.55:8000</span>
          </div>
          <button class="btn-v2 btn-v2--primary">Connect</button>
        </div>
      </section>
      
      <!-- Forms Section -->
      <section v-if="activeTab === 'forms'" class="section">
        <div class="section-header">
          <h2>Form Elements</h2>
          <p>Dark inputs with subtle glass effects</p>
        </div>
        
        <div class="glass-card">
          <div class="form-group">
            <label>Text Input</label>
            <input type="text" class="input-v2" placeholder="IP address or URL" />
          </div>
          
          <div class="form-group">
            <label>Input with Error</label>
            <input type="text" class="input-v2 error" value="invalid-url" />
            <span class="field-error">Invalid URL format</span>
          </div>
          
          <div class="form-group">
            <label>Select Dropdown</label>
            <select class="select-v2">
              <option>Option 1</option>
              <option>Option 2</option>
              <option>Option 3</option>
            </select>
          </div>
          
          <div class="form-row">
            <input type="text" class="input-v2" placeholder="Enter address..." />
            <button class="btn-v2 btn-v2--primary">Add</button>
          </div>
        </div>
      </section>
      
      <!-- Components Section -->
      <section v-if="activeTab === 'components'" class="section">
        <div class="section-header">
          <h2>Components</h2>
          <p>Badges, alerts, dividers, and more</p>
        </div>
        
        <div class="glass-card">
          <h3>Badges</h3>
          <div class="badge-row">
            <span class="badge-v2 badge-v2--success">Connected</span>
            <span class="badge-v2 badge-v2--info">v2.1.0</span>
            <span class="badge-v2 badge-v2--warning">Pending</span>
            <span class="badge-v2 badge-v2--danger">Offline</span>
            <span class="badge-v2 badge-v2--gold">New</span>
          </div>
          
          <div class="divider-v2"><span>Divider</span></div>
          
          <h3>Alerts</h3>
          <div class="alert-v2 alert-v2--warning">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"/>
            </svg>
            Auto-discovery requires the <strong>Preke Studio</strong> desktop app.
          </div>
          
          <div class="alert-v2 alert-v2--info" style="margin-top: 0.75rem;">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
            </svg>
            Scanning network for Preke devices...
          </div>
          
          <div class="alert-v2 alert-v2--success" style="margin-top: 0.75rem;">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/>
            </svg>
            Device connected successfully!
          </div>
          
          <h3 style="margin-top: 1.5rem;">Icon Boxes</h3>
          <div class="icon-box-row">
            <div class="icon-box-v2">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
              </svg>
            </div>
            <div class="icon-box-v2 icon-box-v2--gold">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
              </svg>
            </div>
            <div class="icon-box-v2 icon-box-v2--green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
              </svg>
            </div>
          </div>
          
          <h3 style="margin-top: 1.5rem;">Empty State</h3>
          <div class="empty-state-v2">
            <div class="empty-state-v2__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
                <path d="M9 9l6 6M15 9l-6 6" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </div>
            <p class="empty-state-v2__title">No devices found</p>
            <p class="empty-state-v2__hint">Make sure your Preke device is:</p>
            <ul class="empty-state-v2__checklist">
              <li>Powered on</li>
              <li>Connected to the same network</li>
              <li>Finished booting up (~30 seconds)</li>
            </ul>
          </div>
        </div>
      </section>
      
      <!-- Animations Section -->
      <section v-if="activeTab === 'animations'" class="section">
        <div class="section-header">
          <h2>Animations</h2>
          <p>Smooth transitions and scanning effects</p>
        </div>
        
        <div class="glass-card">
          <h3>Soundwave Scanner</h3>
          <p class="text-muted">Gold gradient bars with staggered animation</p>
          <div class="scan-demo">
            <div class="soundwave-v2">
              <span 
                v-for="i in scanBars" 
                :key="i" 
                class="soundwave-v2__bar" 
                :style="{ '--i': i }"
              ></span>
            </div>
            <p class="scan-label">Scanning 192.168.1.x</p>
          </div>
          
          <div class="divider-v2"><span>Effects</span></div>
          
          <h3>Floating Elements</h3>
          <div class="animation-demo">
            <div class="float-demo animate-float">
              <img src="/logo.svg" alt="Logo" style="width: 64px; height: 64px;" />
            </div>
          </div>
          
          <h3>Pulsing Glow</h3>
          <div class="animation-demo">
            <div class="glow-demo">
              <div class="glow-ring animate-pulse"></div>
              <div class="glow-center"></div>
            </div>
          </div>
          
          <h3>Card Entrance</h3>
          <button class="btn-v2 btn-v2--primary" @click="triggerCardAnimation">
            Replay Animation
          </button>
          <div class="card-animation-demo">
            <div class="mini-card animate-card-appear" key="card-demo">
              Card with 3D entrance
            </div>
          </div>
        </div>
      </section>
      
      <!-- Footer -->
      <footer class="styleguide-v2__footer">
        <span>Preke Studio Design System v2.0</span>
        <span class="text-gold">Corporate Glassmorphism</span>
      </footer>
    </div>
  </div>
</template>

<script lang="ts">
// Extra script for animation trigger
export default {
  methods: {
    triggerCardAnimation() {
      const card = document.querySelector('.mini-card')
      if (card) {
        card.classList.remove('animate-card-appear')
        void (card as HTMLElement).offsetWidth // Trigger reflow
        card.classList.add('animate-card-appear')
      }
    }
  }
}
</script>

<style scoped>
/* Import the design system */
@import '@/styles/design-system-v2.css';

/* ═══════════════════════════════════════════
   STYLE GUIDE LAYOUT
   ═══════════════════════════════════════════ */
.styleguide-v2 {
  min-height: 100vh;
  background: var(--preke-bg-base);
  color: var(--preke-text-primary);
  position: relative;
  overflow-x: hidden;
}

.styleguide-v2__bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.styleguide-v2__bg .bg-orb--1 {
  position: absolute;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.12) 0%, transparent 70%);
  top: -15%;
  right: -10%;
  filter: blur(100px);
  animation: bg-orb-1 15s ease-in-out infinite;
}

.styleguide-v2__bg .bg-orb--2 {
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(168, 153, 104, 0.08) 0%, transparent 70%);
  bottom: -10%;
  left: -10%;
  filter: blur(100px);
  animation: bg-orb-2 18s ease-in-out infinite;
}

@keyframes bg-orb-1 {
  0%, 100% { transform: translate(0, 0); opacity: 0.6; }
  50% { transform: translate(-50px, 80px); opacity: 0.8; }
}

@keyframes bg-orb-2 {
  0%, 100% { transform: translate(0, 0); opacity: 0.5; }
  50% { transform: translate(60px, -60px); opacity: 0.7; }
}

.styleguide-v2__content {
  position: relative;
  z-index: 1;
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

/* ═══════════════════════════════════════════
   HEADER
   ═══════════════════════════════════════════ */
.styleguide-v2__header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--preke-border);
}

.header-logo {
  height: 80px;
  width: auto;
  filter: drop-shadow(0 4px 24px rgba(0, 0, 0, 0.3));
}

.header-text h1 {
  font-size: var(--preke-text-3xl);
  font-weight: 700;
  margin: 0;
}

.header-text p {
  font-size: var(--preke-text-md);
  color: var(--preke-text-muted);
  margin: 0.25rem 0 0;
}

.text-gold {
  color: var(--preke-gold);
}

.text-muted {
  color: var(--preke-text-muted);
}

/* ═══════════════════════════════════════════
   TABS
   ═══════════════════════════════════════════ */
.tabs-nav {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.tab-btn {
  padding: 0.5rem 1rem;
  font-size: var(--preke-text-sm);
  font-weight: 500;
  color: var(--preke-text-muted);
  background: transparent;
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-md);
  cursor: pointer;
  transition: all var(--preke-transition-fast);
}

.tab-btn:hover {
  color: var(--preke-text-primary);
  background: var(--preke-glass-bg-light);
}

.tab-btn.active {
  color: #1a1a1a;
  background: linear-gradient(145deg, var(--preke-gold-light), var(--preke-gold));
  border-color: transparent;
  font-weight: 600;
}

/* ═══════════════════════════════════════════
   SECTIONS
   ═══════════════════════════════════════════ */
.section {
  margin-bottom: 3rem;
}

.section-header {
  margin-bottom: 1.5rem;
}

.section-header h2 {
  font-size: var(--preke-text-2xl);
  font-weight: 600;
  margin: 0;
}

.section-header p {
  font-size: var(--preke-text-md);
  color: var(--preke-text-muted);
  margin: 0.25rem 0 0;
}

/* Glass card overrides for styleguide */
.glass-card {
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.glass-card h3 {
  font-size: var(--preke-text-lg);
  font-weight: 600;
  margin: 0 0 1rem;
  color: var(--preke-text-dim);
}

.glass-card h3:not(:first-child) {
  margin-top: 1.5rem;
}

/* ═══════════════════════════════════════════
   COLOR SWATCHES
   ═══════════════════════════════════════════ */
.color-group {
  margin-bottom: 2rem;
}

.color-group h3 {
  font-size: var(--preke-text-md);
  font-weight: 600;
  color: var(--preke-text-dim);
  margin-bottom: 0.75rem;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 1rem;
}

.color-swatch {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.swatch {
  height: 60px;
  border-radius: var(--preke-radius-md);
  border: 1px solid var(--preke-border);
}

.swatch--text {
  height: 40px;
}

.swatch-name {
  font-size: var(--preke-text-sm);
  font-weight: 500;
  color: var(--preke-text-primary);
}

.swatch-value {
  font-size: var(--preke-text-xs);
  color: var(--preke-text-muted);
  font-family: var(--preke-font-mono);
}

.swatch-var {
  font-size: 0.625rem;
  color: var(--preke-text-subtle);
  font-family: var(--preke-font-mono);
}

/* ═══════════════════════════════════════════
   TYPOGRAPHY SHOWCASE
   ═══════════════════════════════════════════ */
.typography-showcase {
  overflow: hidden;
}

.type-row {
  display: grid;
  grid-template-columns: 100px 1fr auto;
  gap: 1rem;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--preke-border);
}

.type-row:last-of-type {
  border-bottom: none;
}

.type-label {
  font-size: var(--preke-text-sm);
  color: var(--preke-text-muted);
}

.type-sample {
  color: var(--preke-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.type-var {
  font-size: var(--preke-text-xs);
  color: var(--preke-text-subtle);
  font-family: var(--preke-font-mono);
}

.weights-row {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
  padding-top: 0.5rem;
}

.weights-row span {
  font-size: var(--preke-text-md);
  color: var(--preke-text-dim);
}

/* ═══════════════════════════════════════════
   BUTTON ROWS
   ═══════════════════════════════════════════ */
.button-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 1rem;
}

/* ═══════════════════════════════════════════
   CARDS GRID
   ═══════════════════════════════════════════ */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.cards-grid .glass-card p,
.cards-grid .glass-panel p {
  font-size: var(--preke-text-sm);
  color: var(--preke-text-muted);
  margin: 0 0 1rem;
}

/* ═══════════════════════════════════════════
   FORMS
   ═══════════════════════════════════════════ */
.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: var(--preke-text-sm);
  font-weight: 500;
  color: var(--preke-text-dim);
  margin-bottom: 0.5rem;
}

.field-error {
  display: block;
  font-size: var(--preke-text-xs);
  color: var(--preke-red);
  margin-top: 0.25rem;
}

.form-row {
  display: flex;
  gap: 0.5rem;
}

/* ═══════════════════════════════════════════
   BADGES & ICONS
   ═══════════════════════════════════════════ */
.badge-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.icon-box-row {
  display: flex;
  gap: 0.75rem;
}

/* ═══════════════════════════════════════════
   ANIMATIONS DEMO
   ═══════════════════════════════════════════ */
.scan-demo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 0;
}

.scan-label {
  font-size: var(--preke-text-sm);
  color: var(--preke-text-muted);
}

.animation-demo {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.float-demo {
  display: flex;
  align-items: center;
  justify-content: center;
}

.glow-demo {
  position: relative;
  width: 80px;
  height: 80px;
}

.glow-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.3) 0%, transparent 60%);
}

.glow-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--preke-gold);
  box-shadow: 0 0 20px var(--preke-gold-glow);
}

.card-animation-demo {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.mini-card {
  padding: 1rem 1.5rem;
  background: var(--preke-glass-bg);
  border: 1px solid var(--preke-border);
  border-radius: var(--preke-radius-lg);
  font-size: var(--preke-text-sm);
  color: var(--preke-text-dim);
}

/* ═══════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════ */
.styleguide-v2__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 2rem;
  border-top: 1px solid var(--preke-border);
  font-size: var(--preke-text-sm);
  color: var(--preke-text-muted);
}
</style>

