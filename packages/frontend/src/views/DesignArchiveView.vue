<script setup lang="ts">
/**
 * Design Archive - Unified design documentation
 * Combines all design proposals, experiments, and archived designs
 * With thumbnails, categories, search, and sorting
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// Types
type DesignCategory = 'home-page' | 'background' | 'experiment' | 'component' | 'style-guide'
type DesignStatus = 'active' | 'proposed' | 'archived' | 'experiment'

interface DesignItem {
  id: string
  name: string
  description: string
  category: DesignCategory
  status: DesignStatus
  thumbnail?: string
  route?: string
  tags: string[]
  createdAt: string
  updatedAt: string
  details?: {
    features?: string[]
    techStack?: string[]
    notes?: string
  }
}

// All designs data
const designs = ref<DesignItem[]>([
  // ═══════════════════════════════════════════
  // HOME PAGE DESIGNS
  // ═══════════════════════════════════════════
  {
    id: 'combined-parallelograms',
    name: 'Combined Parallelograms',
    description: 'Current home page design with 20 animated parallelograms, alternating 45°/115° rotation, and animated soundwave glimmers.',
    category: 'home-page',
    status: 'active',
    thumbnail: 'combined',
    tags: ['geometric', 'animation', 'parallelogram', 'soundwave'],
    createdAt: '2024-01-05',
    updatedAt: '2024-01-07',
    details: {
      features: ['20 animated shapes', 'Alternating rotation', 'Soundwave animations', 'Mode selection cards'],
      techStack: ['CSS animations', 'Vue transitions', 'clip-path'],
      notes: 'Currently active on the home page. Features soft soundwave animations behind geometric shapes.'
    }
  },
  {
    id: 'split-home',
    name: 'Split Home',
    description: 'Split-screen design with triangular grid background and two distinct sides for each mode.',
    category: 'home-page',
    status: 'proposed',
    thumbnail: 'split',
    route: '/proposals?design=split-home',
    tags: ['split-screen', 'grid', 'recorder', 'mixer'],
    createdAt: '2024-01-04',
    updatedAt: '2024-01-06',
    details: {
      features: ['Vertical split layout', 'Triangular grid pattern', 'Mode-specific colors', 'Hover interactions'],
      techStack: ['CSS Grid', 'SVG patterns', 'CSS transitions']
    }
  },
  {
    id: 'geometric-3d',
    name: 'Geometric 3D',
    description: 'Layered 3D shapes with depth effect and gold highlights casting light on surfaces.',
    category: 'home-page',
    status: 'proposed',
    thumbnail: 'geo3d',
    route: '/proposals?design=geometric-3d',
    tags: ['3d', 'depth', 'gold', 'layers'],
    createdAt: '2024-01-04',
    updatedAt: '2024-01-05',
    details: {
      features: ['3D layered effect', 'Gold light casting', 'Depth shadows', 'Animated glimmers'],
      techStack: ['CSS transforms', 'box-shadow', 'z-index layering']
    }
  },
  {
    id: 'ribbons',
    name: 'Ribbons',
    description: 'Horizontal ribbons with varying opacity and subtle glow animations.',
    category: 'home-page',
    status: 'proposed',
    thumbnail: 'ribbons',
    route: '/proposals?design=ribbons',
    tags: ['ribbons', 'horizontal', 'glow', 'opacity'],
    createdAt: '2024-01-04',
    updatedAt: '2024-01-06',
    details: {
      features: ['Overlapping ribbons', 'Opacity variations', 'Subtle breathing glow', 'Centered alignment'],
      techStack: ['CSS gradients', 'opacity animations', 'backdrop-filter']
    }
  },
  {
    id: 'stock-image',
    name: 'Stock Image Background',
    description: 'Uses the stock image with high contrast, moving light effect, and dark overlay.',
    category: 'home-page',
    status: 'proposed',
    thumbnail: 'stock',
    route: '/proposals?design=stock-image',
    tags: ['image', 'photo', 'contrast', 'overlay'],
    createdAt: '2024-01-04',
    updatedAt: '2024-01-06',
    details: {
      features: ['Stock photo background', 'High contrast filter', 'Moving light effect', 'Dark overlay'],
      techStack: ['CSS filters', 'background-image', 'keyframe animations']
    }
  },
  {
    id: 'cyberpunk',
    name: 'Cyberpunk',
    description: 'Sci-fi circuit grid with neon lines, floating sparks, and ambient glow effects.',
    category: 'home-page',
    status: 'proposed',
    thumbnail: 'cyber',
    route: '/proposals?design=cyberpunk',
    tags: ['cyberpunk', 'neon', 'circuit', 'sci-fi'],
    createdAt: '2024-01-05',
    updatedAt: '2024-01-06',
    details: {
      features: ['Circuit grid pattern', 'Neon line animations', 'Floating spark particles', 'Ambient glow'],
      techStack: ['SVG patterns', 'CSS animations', 'pseudo-elements']
    }
  },
  {
    id: 'original-animated',
    name: 'Original Animated Background',
    description: 'The previous home page design with hexagonal grid, breathing orbs, and circuit traces.',
    category: 'home-page',
    status: 'archived',
    thumbnail: 'original',
    tags: ['hexagon', 'orbs', 'circuit', 'original'],
    createdAt: '2023-12-01',
    updatedAt: '2024-01-05',
    details: {
      features: ['Hexagonal grid', 'Breathing orb animations', 'Circuit trace patterns'],
      notes: 'Replaced by Combined Parallelograms design.'
    }
  },
  
  // ═══════════════════════════════════════════
  // BACKGROUND EXPERIMENTS
  // ═══════════════════════════════════════════
  {
    id: 'breathing-tech',
    name: 'Breathing Tech',
    description: 'Organic breathing animation with subtle center pulse effect on geometric pattern.',
    category: 'experiment',
    status: 'experiment',
    thumbnail: 'breathing',
    route: '/experiments?exp=breathing-tech',
    tags: ['breathing', 'organic', 'pulse', 'geometric'],
    createdAt: '2024-01-03',
    updatedAt: '2024-01-03',
    details: {
      features: ['Scale breathing', 'Center pulse glow', 'Organic feel'],
      techStack: ['CSS scale transforms', 'radial gradients']
    }
  },
  {
    id: 'tron-grid',
    name: 'Tron Grid',
    description: 'Hexagonal overlay with scanning beam lines sweeping across the screen.',
    category: 'experiment',
    status: 'experiment',
    thumbnail: 'tron',
    route: '/experiments?exp=tron-grid',
    tags: ['tron', 'hexagon', 'scan', 'beam'],
    createdAt: '2024-01-03',
    updatedAt: '2024-01-03',
    details: {
      features: ['Hexagonal grid overlay', 'Horizontal scan line', 'Vertical scan line', 'Tron aesthetic'],
      techStack: ['SVG patterns', 'CSS animations', 'linear gradients']
    }
  },
  {
    id: 'circuit-flow',
    name: 'Circuit Flow',
    description: 'Data particles flowing through circuit paths with glowing trails.',
    category: 'experiment',
    status: 'experiment',
    thumbnail: 'circuit',
    route: '/experiments?exp=circuit-flow',
    tags: ['circuit', 'data', 'flow', 'particles'],
    createdAt: '2024-01-03',
    updatedAt: '2024-01-03',
    details: {
      features: ['Circuit path lines', 'Flowing particles', 'Glowing trails'],
      techStack: ['CSS path animations', 'pseudo-elements']
    }
  },
  {
    id: 'holographic',
    name: 'Holographic',
    description: 'Hologram-like distortion with chromatic aberration and scan lines.',
    category: 'experiment',
    status: 'experiment',
    thumbnail: 'holo',
    route: '/experiments?exp=holographic',
    tags: ['holographic', 'distortion', 'chromatic', 'glitch'],
    createdAt: '2024-01-03',
    updatedAt: '2024-01-03',
    details: {
      features: ['Chromatic aberration', 'Scan line overlay', 'Glitch effects'],
      techStack: ['CSS filters', 'pseudo-element overlays']
    }
  },
  {
    id: 'neural-net',
    name: 'Neural Net',
    description: 'Connected nodes pulsing with life, simulating a neural network visualization.',
    category: 'experiment',
    status: 'experiment',
    thumbnail: 'neural',
    route: '/experiments?exp=neural-net',
    tags: ['neural', 'network', 'nodes', 'connections'],
    createdAt: '2024-01-03',
    updatedAt: '2024-01-03',
    details: {
      features: ['Animated nodes', 'Connection lines', 'Pulsing glow'],
      techStack: ['SVG', 'CSS animations', 'pseudo-elements']
    }
  },
  
  // ═══════════════════════════════════════════
  // STYLE GUIDES
  // ═══════════════════════════════════════════
  {
    id: 'style-guide-v1',
    name: 'Style Guide V1',
    description: 'Original design system documentation with colors, typography, and components.',
    category: 'style-guide',
    status: 'archived',
    thumbnail: 'styleguide',
    route: '/styleguide',
    tags: ['colors', 'typography', 'components', 'documentation'],
    createdAt: '2023-11-01',
    updatedAt: '2024-01-01',
    details: {
      features: ['Color tokens', 'Typography scale', 'Component library', 'Interactive examples']
    }
  },
  {
    id: 'style-guide-v2',
    name: 'Style Guide V2',
    description: 'Updated glassmorphism design system with premium dark theme.',
    category: 'style-guide',
    status: 'active',
    thumbnail: 'styleguide2',
    route: '/styleguide-v2',
    tags: ['glassmorphism', 'dark-theme', 'premium', 'modern'],
    createdAt: '2024-01-02',
    updatedAt: '2024-01-07',
    details: {
      features: ['Glassmorphism components', 'Updated color palette', 'Ambient backgrounds', 'Premium feel']
    }
  }
])

// State
const searchQuery = ref('')
const selectedCategory = ref<DesignCategory | 'all'>('all')
const selectedStatus = ref<DesignStatus | 'all'>('all')
const sortBy = ref<'name' | 'date' | 'status'>('date')
const sortOrder = ref<'asc' | 'desc'>('desc')
const selectedDesign = ref<DesignItem | null>(null)

// Categories for filter
const categories: { value: DesignCategory | 'all'; label: string; icon: string }[] = [
  { value: 'all', label: 'All', icon: '📁' },
  { value: 'home-page', label: 'Home Page', icon: '🏠' },
  { value: 'background', label: 'Background', icon: '🎨' },
  { value: 'experiment', label: 'Experiment', icon: '🧪' },
  { value: 'style-guide', label: 'Style Guide', icon: '📐' }
]

// Statuses for filter
const statuses: { value: DesignStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'proposed', label: 'Proposed' },
  { value: 'experiment', label: 'Experiment' },
  { value: 'archived', label: 'Archived' }
]

// Computed filtered and sorted designs
const filteredDesigns = computed(() => {
  let result = [...designs.value]
  
  // Filter by search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(d => 
      d.name.toLowerCase().includes(query) ||
      d.description.toLowerCase().includes(query) ||
      d.tags.some(t => t.toLowerCase().includes(query))
    )
  }
  
  // Filter by category
  if (selectedCategory.value !== 'all') {
    result = result.filter(d => d.category === selectedCategory.value)
  }
  
  // Filter by status
  if (selectedStatus.value !== 'all') {
    result = result.filter(d => d.status === selectedStatus.value)
  }
  
  // Sort
  result.sort((a, b) => {
    let comparison = 0
    switch (sortBy.value) {
      case 'name':
        comparison = a.name.localeCompare(b.name)
        break
      case 'date':
        comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime()
        break
      case 'status':
        const statusOrder = { active: 0, proposed: 1, experiment: 2, archived: 3 }
        comparison = statusOrder[a.status] - statusOrder[b.status]
        break
    }
    return sortOrder.value === 'desc' ? -comparison : comparison
  })
  
  return result
})

// Helpers
function getStatusColor(status: DesignStatus) {
  switch (status) {
    case 'active': return 'var(--preke-green)'
    case 'proposed': return 'var(--preke-gold)'
    case 'experiment': return 'var(--preke-blue)'
    case 'archived': return 'var(--preke-text-muted)'
  }
}

function getStatusLabel(status: DesignStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function getCategoryLabel(category: DesignCategory) {
  return categories.find(c => c.value === category)?.label || category
}

function getCategoryIcon(category: DesignCategory) {
  return categories.find(c => c.value === category)?.icon || '📁'
}

function getThumbnailGradient(design: DesignItem) {
  // Generate a unique gradient based on design properties
  const gradients: Record<string, string> = {
    'combined': 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    'split': 'linear-gradient(90deg, #2d1f3d 0%, #1a1a2e 50%, #1e3a5f 100%)',
    'geo3d': 'linear-gradient(135deg, #1a1a2e 0%, #2d2d44 50%, #1a1a2e 100%)',
    'ribbons': 'linear-gradient(180deg, #1a1a2e 0%, #2d1f3d 100%)',
    'stock': 'linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%)',
    'cyber': 'linear-gradient(135deg, #0a0a1a 0%, #1a0a2a 50%, #0a1a2a 100%)',
    'original': 'linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%)',
    'breathing': 'linear-gradient(135deg, #1a2a1a 0%, #1a1a2e 100%)',
    'tron': 'linear-gradient(135deg, #0a1a2a 0%, #1a2a3a 100%)',
    'circuit': 'linear-gradient(135deg, #1a1a2e 0%, #2a1a3e 100%)',
    'holo': 'linear-gradient(135deg, #2a1a3e 0%, #1a2a3e 50%, #3a1a2e 100%)',
    'neural': 'linear-gradient(135deg, #1a2a2e 0%, #1a1a3e 100%)',
    'styleguide': 'linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)',
    'styleguide2': 'linear-gradient(135deg, #1a1a2e 0%, #2a2a3e 100%)'
  }
  return gradients[design.thumbnail || ''] || 'linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)'
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  })
}

function viewDesign(design: DesignItem) {
  if (design.route) {
    router.push(design.route)
  } else {
    selectedDesign.value = design
  }
}

function closeDetail() {
  selectedDesign.value = null
}

function toggleSortOrder() {
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
}
</script>

<template>
  <div class="archive">
    <!-- Back button -->
    <button class="archive__back" @click="router.push('/admin')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      Back to Settings
    </button>
    
    <!-- Header -->
    <div class="archive__header">
      <h1>Design Archive</h1>
      <p>All design proposals, experiments, and archived variations for Preke Studio.</p>
    </div>
    
    <!-- Search and Filters -->
    <div class="archive__controls">
      <!-- Search -->
      <div class="archive__search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input 
          v-model="searchQuery"
          type="text" 
          placeholder="Search designs..."
          class="archive__search-input"
        />
      </div>
      
      <!-- Category Filter -->
      <div class="archive__filter-group">
        <button 
          v-for="cat in categories"
          :key="cat.value"
          @click="selectedCategory = cat.value"
          class="archive__filter-btn"
          :class="{ 'archive__filter-btn--active': selectedCategory === cat.value }"
        >
          <span class="archive__filter-icon">{{ cat.icon }}</span>
          {{ cat.label }}
        </button>
      </div>
      
      <!-- Status & Sort -->
      <div class="archive__sort-row">
        <select v-model="selectedStatus" class="archive__select">
          <option v-for="s in statuses" :key="s.value" :value="s.value">
            {{ s.label }}
          </option>
        </select>
        
        <select v-model="sortBy" class="archive__select">
          <option value="date">Sort by Date</option>
          <option value="name">Sort by Name</option>
          <option value="status">Sort by Status</option>
        </select>
        
        <button @click="toggleSortOrder" class="archive__sort-btn" :title="sortOrder === 'asc' ? 'Ascending' : 'Descending'">
          <svg v-if="sortOrder === 'desc'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12l7 7 7-7"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 19V5M5 12l7-7 7 7"/>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Results count -->
    <div class="archive__results-count">
      {{ filteredDesigns.length }} design{{ filteredDesigns.length !== 1 ? 's' : '' }} found
    </div>
    
    <!-- Design Grid -->
    <div class="archive__grid">
      <div 
        v-for="design in filteredDesigns" 
        :key="design.id"
        class="archive__card"
        :class="{ 'archive__card--clickable': design.route }"
        @click="viewDesign(design)"
      >
        <!-- Thumbnail -->
        <div class="archive__thumbnail" :style="{ background: getThumbnailGradient(design) }">
          <div class="archive__thumbnail-overlay">
            <span class="archive__category-badge">
              {{ getCategoryIcon(design.category) }} {{ getCategoryLabel(design.category) }}
            </span>
          </div>
          <!-- Decorative elements based on design type -->
          <div v-if="design.thumbnail === 'combined'" class="thumb-deco thumb-deco--parallelograms">
            <div class="thumb-shape"></div>
            <div class="thumb-shape"></div>
            <div class="thumb-shape"></div>
          </div>
          <div v-else-if="design.thumbnail === 'split'" class="thumb-deco thumb-deco--split">
            <div class="thumb-line"></div>
          </div>
          <div v-else-if="design.thumbnail === 'cyber'" class="thumb-deco thumb-deco--cyber">
            <div class="thumb-circuit"></div>
          </div>
          <div v-else class="thumb-deco thumb-deco--default">
            <div class="thumb-orb"></div>
          </div>
        </div>
        
        <!-- Content -->
        <div class="archive__card-content">
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
          
          <!-- Tags -->
          <div class="archive__tags">
            <span v-for="tag in design.tags.slice(0, 3)" :key="tag" class="archive__tag">
              {{ tag }}
            </span>
            <span v-if="design.tags.length > 3" class="archive__tag archive__tag--more">
              +{{ design.tags.length - 3 }}
            </span>
          </div>
          
          <!-- Footer -->
          <div class="archive__card-footer">
            <span class="archive__date">Updated {{ formatDate(design.updatedAt) }}</span>
            <span v-if="design.route" class="archive__action">
              View →
            </span>
            <span v-else class="archive__action archive__action--details">
              Details →
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Empty state -->
    <div v-if="filteredDesigns.length === 0" class="archive__empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
      </svg>
      <h3>No designs found</h3>
      <p>Try adjusting your search or filters</p>
    </div>
    
    <!-- Related Links -->
    <div class="archive__links">
      <h2>Quick Links</h2>
      <div class="archive__link-grid">
        <router-link to="/proposals" class="archive__link">
          <div class="archive__link-icon">🎨</div>
          <div>
            <h4>Interactive Proposals</h4>
            <p>View live design demos</p>
          </div>
        </router-link>
        
        <router-link to="/experiments" class="archive__link">
          <div class="archive__link-icon">🧪</div>
          <div>
            <h4>Background Experiments</h4>
            <p>Sci-fi animation tests</p>
          </div>
        </router-link>
        
        <router-link to="/styleguide-v2" class="archive__link">
          <div class="archive__link-icon">📐</div>
          <div>
            <h4>Style Guide V2</h4>
            <p>Design system docs</p>
          </div>
        </router-link>
      </div>
    </div>
    
    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="selectedDesign" class="archive__modal-overlay" @click="closeDetail">
        <div class="archive__modal" @click.stop>
          <button class="archive__modal-close" @click="closeDetail">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
          
          <div class="archive__modal-thumb" :style="{ background: getThumbnailGradient(selectedDesign) }">
            <span 
              class="archive__status archive__status--large"
              :style="{ color: getStatusColor(selectedDesign.status), borderColor: getStatusColor(selectedDesign.status) }"
            >
              {{ getStatusLabel(selectedDesign.status) }}
            </span>
          </div>
          
          <div class="archive__modal-content">
            <h2>{{ selectedDesign.name }}</h2>
            <p class="archive__modal-desc">{{ selectedDesign.description }}</p>
            
            <div class="archive__modal-meta">
              <div class="archive__modal-meta-item">
                <span class="label">Category</span>
                <span class="value">{{ getCategoryIcon(selectedDesign.category) }} {{ getCategoryLabel(selectedDesign.category) }}</span>
              </div>
              <div class="archive__modal-meta-item">
                <span class="label">Created</span>
                <span class="value">{{ formatDate(selectedDesign.createdAt) }}</span>
              </div>
              <div class="archive__modal-meta-item">
                <span class="label">Updated</span>
                <span class="value">{{ formatDate(selectedDesign.updatedAt) }}</span>
              </div>
            </div>
            
            <div v-if="selectedDesign.details?.features" class="archive__modal-section">
              <h4>Features</h4>
              <ul>
                <li v-for="feature in selectedDesign.details.features" :key="feature">
                  {{ feature }}
                </li>
              </ul>
            </div>
            
            <div v-if="selectedDesign.details?.techStack" class="archive__modal-section">
              <h4>Tech Stack</h4>
              <div class="archive__modal-tags">
                <span v-for="tech in selectedDesign.details.techStack" :key="tech" class="archive__tag">
                  {{ tech }}
                </span>
              </div>
            </div>
            
            <div v-if="selectedDesign.details?.notes" class="archive__modal-section">
              <h4>Notes</h4>
              <p>{{ selectedDesign.details.notes }}</p>
            </div>
            
            <div class="archive__modal-section">
              <h4>Tags</h4>
              <div class="archive__modal-tags">
                <span v-for="tag in selectedDesign.tags" :key="tag" class="archive__tag">
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.archive {
  padding: 2rem;
  max-width: 1400px;
  height: 100%;
  overflow-y: auto;
}

/* Back button */
.archive__back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  margin-bottom: 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--preke-text-muted);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.archive__back:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--preke-text);
  border-color: rgba(255, 255, 255, 0.2);
}

.archive__back svg {
  width: 18px;
  height: 18px;
}

/* Header */
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

/* Controls */
.archive__controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.archive__search {
  position: relative;
  max-width: 400px;
}

.archive__search svg {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: var(--preke-text-muted);
  pointer-events: none;
}

.archive__search-input {
  width: 100%;
  padding: 10px 12px 10px 40px;
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 8px;
  color: var(--preke-text);
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
}

.archive__search-input:focus {
  border-color: var(--preke-gold);
  box-shadow: 0 0 0 3px rgba(224, 160, 48, 0.1);
}

.archive__search-input::placeholder {
  color: var(--preke-text-subtle);
}

/* Filter buttons */
.archive__filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.archive__filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 100px;
  color: var(--preke-text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.archive__filter-btn:hover {
  border-color: var(--preke-gold);
  color: var(--preke-text);
}

.archive__filter-btn--active {
  background: rgba(224, 160, 48, 0.15);
  border-color: var(--preke-gold);
  color: var(--preke-gold);
}

.archive__filter-icon {
  font-size: 14px;
}

/* Sort row */
.archive__sort-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.archive__select {
  padding: 8px 12px;
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 8px;
  color: var(--preke-text);
  font-size: 13px;
  cursor: pointer;
  outline: none;
}

.archive__select:focus {
  border-color: var(--preke-gold);
}

.archive__sort-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 8px;
  color: var(--preke-text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
}

.archive__sort-btn:hover {
  border-color: var(--preke-gold);
  color: var(--preke-text);
}

.archive__sort-btn svg {
  width: 18px;
  height: 18px;
}

/* Results count */
.archive__results-count {
  font-size: 13px;
  color: var(--preke-text-subtle);
  margin-bottom: 1rem;
}

/* Grid */
.archive__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.25rem;
  margin-bottom: 3rem;
}

/* Card */
.archive__card {
  background: var(--preke-surface);
  border: 1px solid var(--preke-border);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s ease;
  cursor: pointer;
}

.archive__card:hover {
  border-color: var(--preke-gold);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

/* Thumbnail */
.archive__thumbnail {
  position: relative;
  height: 120px;
  overflow: hidden;
}

.archive__thumbnail-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 10px;
  display: flex;
  justify-content: flex-end;
}

.archive__category-badge {
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  padding: 4px 10px;
  border-radius: 100px;
  font-size: 11px;
  color: var(--preke-text);
  font-weight: 500;
}

/* Thumbnail decorations */
.thumb-deco {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.thumb-deco--parallelograms {
  gap: 8px;
}

.thumb-deco--parallelograms .thumb-shape {
  width: 30px;
  height: 50px;
  background: rgba(224, 160, 48, 0.2);
  border: 1px solid rgba(224, 160, 48, 0.3);
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
}

.thumb-deco--parallelograms .thumb-shape:nth-child(2) {
  transform: rotate(45deg);
  background: rgba(224, 160, 48, 0.15);
}

.thumb-deco--parallelograms .thumb-shape:nth-child(3) {
  transform: rotate(-30deg);
  background: rgba(224, 160, 48, 0.1);
}

.thumb-deco--split .thumb-line {
  width: 2px;
  height: 60%;
  background: linear-gradient(180deg, transparent, rgba(255, 255, 255, 0.3), transparent);
}

.thumb-deco--cyber .thumb-circuit {
  width: 60%;
  height: 60%;
  border: 1px solid rgba(92, 225, 230, 0.3);
  border-radius: 4px;
  position: relative;
}

.thumb-deco--cyber .thumb-circuit::before {
  content: '';
  position: absolute;
  top: 50%;
  left: -20px;
  right: -20px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(92, 225, 230, 0.5), transparent);
}

.thumb-deco--default .thumb-orb {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(224, 160, 48, 0.3), transparent);
  box-shadow: 0 0 30px rgba(224, 160, 48, 0.2);
}

/* Card content */
.archive__card-content {
  padding: 1rem;
}

.archive__card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.archive__card-header h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--preke-text);
  line-height: 1.3;
}

.archive__status {
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.2rem 0.5rem;
  border-radius: 100px;
  border: 1px solid;
  white-space: nowrap;
  flex-shrink: 0;
}

.archive__status--large {
  font-size: 0.7rem;
  padding: 0.3rem 0.75rem;
}

.archive__description {
  font-size: 0.8rem;
  color: var(--preke-text-muted);
  line-height: 1.5;
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Tags */
.archive__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}

.archive__tag {
  font-size: 0.65rem;
  padding: 0.15rem 0.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: var(--preke-text-subtle);
}

.archive__tag--more {
  background: rgba(224, 160, 48, 0.1);
  border-color: rgba(224, 160, 48, 0.2);
  color: var(--preke-gold);
}

/* Card footer */
.archive__card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.75rem;
  border-top: 1px solid var(--preke-border);
}

.archive__date {
  font-size: 0.7rem;
  color: var(--preke-text-subtle);
}

.archive__action {
  font-size: 0.75rem;
  color: var(--preke-gold);
  font-weight: 500;
}

.archive__action--details {
  color: var(--preke-text-muted);
}

/* Empty state */
.archive__empty {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--preke-text-muted);
}

.archive__empty svg {
  width: 48px;
  height: 48px;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.archive__empty h3 {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
  color: var(--preke-text);
}

/* Links section */
.archive__links {
  border-top: 1px solid var(--preke-border);
  padding-top: 2rem;
}

.archive__links h2 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.archive__link-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
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
  font-size: 24px;
  flex-shrink: 0;
}

.archive__link h4 {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.125rem;
}

.archive__link p {
  font-size: 0.7rem;
  color: var(--preke-text-muted);
}

/* Modal */
.archive__modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.archive__modal {
  position: relative;
  background: var(--preke-bg-elevated);
  border: 1px solid var(--preke-border);
  border-radius: 16px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.archive__modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  border-radius: 50%;
  color: var(--preke-text);
  cursor: pointer;
  z-index: 1;
  transition: all 0.2s ease;
}

.archive__modal-close:hover {
  background: rgba(0, 0, 0, 0.7);
}

.archive__modal-close svg {
  width: 18px;
  height: 18px;
}

.archive__modal-thumb {
  height: 160px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding: 1rem;
}

.archive__modal-content {
  padding: 1.5rem;
}

.archive__modal-content h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 0.5rem;
}

.archive__modal-desc {
  color: var(--preke-text-muted);
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.archive__modal-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 1rem;
  background: var(--preke-surface);
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.archive__modal-meta-item {
  text-align: center;
}

.archive__modal-meta-item .label {
  display: block;
  font-size: 0.7rem;
  color: var(--preke-text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.archive__modal-meta-item .value {
  font-size: 0.85rem;
  color: var(--preke-text);
  font-weight: 500;
}

.archive__modal-section {
  margin-bottom: 1.5rem;
}

.archive__modal-section h4 {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.archive__modal-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.archive__modal-section li {
  position: relative;
  padding-left: 1.25rem;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  color: var(--preke-text-muted);
}

.archive__modal-section li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--preke-gold);
}

.archive__modal-section p {
  font-size: 0.85rem;
  color: var(--preke-text-muted);
  line-height: 1.6;
}

.archive__modal-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
