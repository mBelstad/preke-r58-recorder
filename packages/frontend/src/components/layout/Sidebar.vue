<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

interface NavItem {
  id: string
  label: string
  path: string
  icon: string
}

const navItems: NavItem[] = [
  { id: 'studio', label: 'Studio', path: '/', icon: 'home' },
  { id: 'recorder', label: 'Recorder', path: '/recorder', icon: 'record' },
  { id: 'mixer', label: 'Mixer', path: '/mixer', icon: 'mixer' },
  { id: 'library', label: 'Library', path: '/library', icon: 'folder' },
  { id: 'admin', label: 'Admin', path: '/admin', icon: 'settings' },
]

const currentPath = computed(() => route.path)

function isActive(path: string): boolean {
  return currentPath.value === path
}
</script>

<template>
  <aside class="w-20 bg-r58-bg-secondary border-r border-r58-bg-tertiary flex flex-col">
    <!-- Logo -->
    <div class="h-16 flex items-center justify-center border-b border-r58-bg-tertiary">
      <span class="text-xl font-bold text-r58-accent-primary">R58</span>
    </div>
    
    <!-- Navigation -->
    <nav class="flex-1 py-4">
      <ul class="space-y-2 px-2">
        <li v-for="item in navItems" :key="item.id">
          <router-link
            :to="item.path"
            class="flex flex-col items-center gap-1 py-3 px-2 rounded-lg transition-colors"
            :class="[
              isActive(item.path)
                ? 'bg-r58-accent-primary/10 text-r58-accent-primary'
                : 'text-r58-text-secondary hover:text-r58-text-primary hover:bg-r58-bg-tertiary'
            ]"
          >
            <!-- Icons -->
            <svg v-if="item.icon === 'home'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
            </svg>
            <svg v-else-if="item.icon === 'record'" class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="8"/>
            </svg>
            <svg v-else-if="item.icon === 'mixer'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
            </svg>
            <svg v-else-if="item.icon === 'folder'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
            </svg>
            <svg v-else-if="item.icon === 'settings'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            
            <span class="text-xs font-medium">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>
    
    <!-- Version -->
    <div class="p-2 text-center text-xs text-r58-text-secondary">
      v2.0.0
    </div>
  </aside>
</template>

