<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Session {
  id: string
  name: string
  date: string
  duration: string
  fileCount: number
  totalSize: string
}

const sessions = ref<Session[]>([])
const loading = ref(true)

onMounted(async () => {
  // TODO: Fetch from API
  sessions.value = [
    {
      id: '1',
      name: 'Sunday Service',
      date: '2024-12-28',
      duration: '1:45:32',
      fileCount: 4,
      totalSize: '12.4 GB'
    },
    {
      id: '2',
      name: 'Wednesday Bible Study',
      date: '2024-12-25',
      duration: '0:58:15',
      fileCount: 2,
      totalSize: '4.2 GB'
    }
  ]
  loading.value = false
})
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-r58-bg-tertiary bg-r58-bg-secondary">
      <h1 class="text-xl font-semibold">Recording Library</h1>
      <div class="flex items-center gap-4">
        <input 
          type="search" 
          placeholder="Search recordings..."
          class="input w-64"
        />
      </div>
    </header>
    
    <!-- Content -->
    <div class="flex-1 p-6 overflow-y-auto">
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="animate-spin w-8 h-8 border-2 border-r58-accent-primary border-t-transparent rounded-full"></div>
      </div>
      
      <div v-else class="grid gap-4">
        <div 
          v-for="session in sessions" 
          :key="session.id"
          class="card flex items-center justify-between hover:border-r58-accent-primary/50 transition-colors cursor-pointer"
        >
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-lg bg-r58-bg-tertiary flex items-center justify-center">
              <svg class="w-6 h-6 text-r58-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
            </div>
            <div>
              <h3 class="font-medium">{{ session.name }}</h3>
              <p class="text-sm text-r58-text-secondary">{{ session.date }} · {{ session.duration }}</p>
            </div>
          </div>
          
          <div class="flex items-center gap-6 text-sm text-r58-text-secondary">
            <span>{{ session.fileCount }} files</span>
            <span>{{ session.totalSize }}</span>
            <button class="btn">Open</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

