<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface DesignItem {
  id: string
  name: string
  description: string
  status: 'active' | 'archived' | 'proposed'
  route?: string
}

const designs = ref<DesignItem[]>([
  {
    id: 'combined',
    name: 'Combined Parallelograms',
    description: 'Current home page design with 20 animated parallelograms, alternating 45°/115° rotation, and gold glimmers.',
    status: 'active'
  },
  {
    id: 'split-home',
    name: 'Split Home',
    description: 'Split-screen design with triangular grid background and two distinct sides for each mode.',
    status: 'proposed',
    route: '/proposals'
  },
  {
    id: 'geometric-3d',
    name: 'Geometric 3D',
    description: 'Layered 3D shapes with depth effect and gold highlights casting light on surfaces.',
    status: 'proposed',
    route: '/proposals'
  },
  {
    id: 'ribbons',
    name: 'Ribbons',
    description: 'Horizontal ribbons with varying opacity and subtle glow animations.',
    status: 'proposed',
    route: '/proposals'
  },
  {
    id: 'stock-image',
    name: 'Stock Image Background',
    description: 'Uses the stock image with high contrast, moving light effect, and dark overlay.',
    status: 'proposed',
    route: '/proposals'
  },
  {
    id: 'cyberpunk',
    name: 'Cyberpunk',
    description: 'Sci-fi circuit grid with neon lines, floating sparks, and ambient glow effects.',
    status: 'proposed',
    route: '/proposals'
  },
  {
    id: 'animated-bg-original',
    name: 'Original Animated Background',
    description: 'The previous home page design with hexagonal grid, breathing orbs, and circuit traces.',
    status: 'archived'
  }
])

function viewDesign(design: DesignItem) {
  if (design.route) {
    router.push(design.route)
  }
}

function getStatusColor(status: string) {
  switch (status) {
    case 'active': return 'var(--preke-green)'
    case 'proposed': return 'var(--preke-gold)'
    case 'archived': return 'var(--preke-text-muted)'
    default: return 'var(--preke-text-muted)'
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case 'active': return 'Active'
    case 'proposed': return 'Proposed'
    case 'archived': return 'Archived'
    default: return status
  }
}
</script>

<template>
  <div class="archive">
    <div class="archive__header">
      <h1>Design Archive</h1>
      <p>All past, current, and proposed design variations for Preke Studio.</p>
    </div>
    
    <div class="archive__grid">
      <div 
        v-for="design in designs" 
        :key="design.id"
        class="archive__card"
        :class="{ 'archive__card--clickable': design.route }"
        @click="viewDesign(design)"
      >
        <div class="archive__card-header">
          <h3>{{ design.name }}</h3>
          <span 
            class="archive__status"
            :style="{ color: getStatusColor(design.status), borderColor: getStatusColor(design.status) }"
          >
            {{ getStatusLabel(design.status) }}
          </span>
        </div>
        <p class="archive__description">{{ design.description }}</p>
        <div v-if="design.route" class="archive__action">
          <span>View in Proposals →</span>
        </div>
      </div>
    </div>
    
    <div class="archive__links">
      <h2>Related Pages</h2>
      <div class="archive__link-grid">
        <router-link to="/proposals" class="archive__link">
          <div class="archive__link-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>
            </svg>
          </div>
          <div>
            <h4>Design Proposals</h4>
            <p>Interactive preview of proposed designs</p>
          </div>
        </router-link>
        
        <router-link to="/styleguide" class="archive__link">
          <div class="archive__link-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
            </svg>
          </div>
          <div>
            <h4>Style Guide</h4>
            <p>Colors, typography, and component library</p>
          </div>
        </router-link>
        
        <router-link to="/styleguide-v2" class="archive__link">
          <div class="archive__link-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
          <div>
            <h4>Style Guide V2</h4>
            <p>Updated design system documentation</p>
          </div>
        </router-link>
        
        <router-link to="/experiments" class="archive__link">
          <div class="archive__link-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/>
            </svg>
          </div>
          <div>
            <h4>Background Experiments</h4>
            <p>Experimental background animations</p>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.archive {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.archive__header {
  margin-bottom: 2rem;
}

.archive__header h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.archive__header p {
  color: var(--preke-text-muted);
}

.archive__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
  margin-bottom: 3rem;
}

.archive__card {
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 12px;
  padding: 1.25rem;
  transition: all 0.2s ease;
}

.archive__card--clickable {
  cursor: pointer;
}

.archive__card--clickable:hover {
  border-color: var(--preke-gold);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.archive__card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.archive__card-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--preke-text);
}

.archive__status {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.25rem 0.5rem;
  border-radius: 100px;
  border: 1px solid;
  white-space: nowrap;
}

.archive__description {
  font-size: 0.875rem;
  color: var(--preke-text-muted);
  line-height: 1.5;
}

.archive__action {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--preke-border);
}

.archive__action span {
  font-size: 0.8rem;
  color: var(--preke-gold);
  font-weight: 500;
}

.archive__links {
  border-top: 1px solid var(--preke-border);
  padding-top: 2rem;
}

.archive__links h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.archive__link-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.archive__link {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 10px;
  text-decoration: none;
  transition: all 0.2s ease;
}

.archive__link:hover {
  border-color: var(--preke-gold);
  background: rgba(224, 160, 48, 0.05);
}

.archive__link-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(224, 160, 48, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.archive__link-icon svg {
  width: 20px;
  height: 20px;
  color: var(--preke-gold);
}

.archive__link h4 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.125rem;
}

.archive__link p {
  font-size: 0.75rem;
  color: var(--preke-text-muted);
}
</style>

