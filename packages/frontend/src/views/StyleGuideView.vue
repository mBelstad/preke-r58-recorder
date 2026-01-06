<script setup lang="ts">
/**
 * StyleGuideView - R58 Design System Documentation
 * 
 * A visual playground for all design tokens and components.
 * Useful for:
 * - Verifying design consistency
 * - Testing component variants
 * - Reference for developers
 * - Visual regression testing
 */
import { ref } from 'vue'
import BaseModal from '@/components/shared/BaseModal.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'

const modalRef = ref<InstanceType<typeof BaseModal> | null>(null)
const confirmDialogRef = ref<InstanceType<typeof ConfirmDialog> | null>(null)

const colorTokens = [
  { name: 'Background Base', var: '--preke-bg-base', class: 'bg-preke-bg-base' },
  { name: 'Background Elevated', var: '--preke-bg-elevated', class: 'bg-preke-bg-elevated' },
  { name: 'Background Surface', var: '--preke-bg-surface', class: 'bg-preke-bg-surface' },
  { name: 'Text Primary', var: '--preke-text', class: 'text-preke-text bg-preke-bg-elevated' },
  { name: 'Text Dim', var: '--preke-text-dim', class: 'text-preke-text-dim bg-preke-bg-elevated' },
  { name: 'Text Muted', var: '--preke-text-muted', class: 'text-preke-text-muted bg-preke-bg-elevated' },
  { name: 'Gold', var: '--preke-gold', class: 'bg-preke-gold' },
  { name: 'Green', var: '--preke-green', class: 'bg-preke-green' },
  { name: 'Red', var: '--preke-red', class: 'bg-preke-red' },
  { name: 'Amber', var: '--preke-amber', class: 'bg-preke-amber' },
  { name: 'Mode Recorder', var: '--preke-red', class: 'bg-preke-red' },
  { name: 'Mode Mixer', var: '--preke-purple', class: 'bg-preke-purple' },
]

const typographySizes = [
  { name: 'XS (12px)', class: 'text-xs', sample: 'The quick brown fox' },
  { name: 'SM (14px)', class: 'text-sm', sample: 'The quick brown fox' },
  { name: 'Base (16px)', class: 'text-base', sample: 'The quick brown fox' },
  { name: 'LG (18px)', class: 'text-lg', sample: 'The quick brown fox' },
  { name: 'XL (20px)', class: 'text-xl', sample: 'The quick brown fox' },
  { name: '2XL (24px)', class: 'text-2xl', sample: 'The quick brown fox' },
]

const textInput = ref('')
const selectValue = ref('option1')
const textareaValue = ref('')
const checkboxValue = ref(false)
const activeTab = ref('tab1')

function openModal() {
  modalRef.value?.open()
}

function openConfirmDialog() {
  confirmDialogRef.value?.open()
}
</script>

<template>
  <div class="h-full overflow-y-auto p-8 bg-preke-bg-base">
    <div class="max-w-6xl mx-auto space-y-12">
      <!-- Header -->
      <div class="text-center mb-12">
        <h1 class="text-4xl font-bold mb-2">Preke Design System</h1>
        <p class="text-preke-text-dim">
          A comprehensive guide to colors, typography, and components
        </p>
      </div>

      <!-- Color Tokens -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Color Tokens</h2>
          <p class="card-description">Semantic color palette with CSS variable references</p>
        </div>
        
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <div
            v-for="token in colorTokens"
            :key="token.name"
            class="space-y-2"
          >
            <div :class="['h-20 rounded-lg border-2 border-preke-bg-surface', token.class]"></div>
            <div>
              <div class="text-sm font-medium">{{ token.name }}</div>
              <div class="text-xs text-preke-text-dim font-mono">{{ token.var }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Typography -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Typography Scale</h2>
          <p class="card-description">Font sizes and weights</p>
        </div>
        
        <div class="space-y-4">
          <div v-for="size in typographySizes" :key="size.name">
            <div class="flex items-baseline gap-4">
              <span class="text-sm text-preke-text-dim w-32">{{ size.name }}</span>
              <span :class="[size.class]">{{ size.sample }}</span>
            </div>
          </div>
          
          <div class="divider"></div>
          
          <div class="space-y-2">
            <div class="text-base font-normal">Normal weight text</div>
            <div class="text-base font-medium">Medium weight text</div>
            <div class="text-base font-semibold">Semibold weight text</div>
            <div class="text-base font-bold">Bold weight text</div>
          </div>
        </div>
      </section>

      <!-- Buttons -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Buttons</h2>
          <p class="card-description">Button variants and sizes</p>
        </div>
        
        <div class="space-y-6">
          <!-- Default buttons -->
          <div>
            <h3 class="text-sm font-semibold mb-3 text-preke-text-dim">Variants</h3>
            <div class="flex flex-wrap gap-3">
              <button class="btn">Default</button>
              <button class="btn btn-primary">Primary</button>
              <button class="btn btn-success">Success</button>
              <button class="btn btn-danger">Danger</button>
              <button class="btn btn-ghost">Ghost</button>
              <button class="btn" disabled>Disabled</button>
            </div>
          </div>
          
          <!-- Sizes -->
          <div>
            <h3 class="text-sm font-semibold mb-3 text-preke-text-dim">Sizes</h3>
            <div class="flex flex-wrap items-end gap-3">
              <button class="btn btn-primary text-sm px-3 py-1.5">Small</button>
              <button class="btn btn-primary">Default</button>
              <button class="btn btn-primary btn-lg">Large</button>
              <button class="btn btn-primary btn-xl">Extra Large</button>
            </div>
          </div>
          
          <!-- With icons -->
          <div>
            <h3 class="text-sm font-semibold mb-3 text-preke-text-dim">With Icons</h3>
            <div class="flex flex-wrap gap-3">
              <button class="btn btn-primary">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Add Item
              </button>
              <button class="btn btn-danger">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Form Elements -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Form Elements</h2>
          <p class="card-description">Inputs, selects, and form controls</p>
        </div>
        
        <div class="space-y-4">
          <!-- Text input -->
          <div>
            <label class="block text-sm font-medium mb-2">Text Input</label>
            <input v-model="textInput" type="text" class="input w-full" placeholder="Enter text..." />
          </div>
          
          <!-- Select -->
          <div>
            <label class="block text-sm font-medium mb-2">Select Dropdown</label>
            <select v-model="selectValue" class="input w-full">
              <option value="option1">Option 1</option>
              <option value="option2">Option 2</option>
              <option value="option3">Option 3</option>
            </select>
          </div>
          
          <!-- Textarea -->
          <div>
            <label class="block text-sm font-medium mb-2">Textarea</label>
            <textarea v-model="textareaValue" class="input w-full" placeholder="Enter multiple lines..." rows="3"></textarea>
          </div>
          
          <!-- Checkbox -->
          <div>
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="checkboxValue" type="checkbox" class="w-5 h-5 rounded bg-preke-bg-surface border-2 border-preke-bg-surface checked:bg-preke-gold checked:border-preke-gold" />
              <span class="text-sm">I agree to the terms and conditions</span>
            </label>
          </div>
        </div>
      </section>

      <!-- Badges -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Badges</h2>
          <p class="card-description">Status indicators and labels</p>
        </div>
        
        <div class="flex flex-wrap gap-3">
          <span class="badge badge-success">Success</span>
          <span class="badge badge-danger">Danger</span>
          <span class="badge badge-warning">Warning</span>
          <span class="badge badge-info">Info</span>
        </div>
      </section>

      <!-- Alerts -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Alerts</h2>
          <p class="card-description">Notification and message boxes</p>
        </div>
        
        <div class="space-y-3">
          <div class="alert alert-info">
            <strong>Info:</strong> This is an informational message.
          </div>
          <div class="alert alert-success">
            <strong>Success:</strong> Operation completed successfully!
          </div>
          <div class="alert alert-warning">
            <strong>Warning:</strong> Please review this before proceeding.
          </div>
          <div class="alert alert-danger">
            <strong>Error:</strong> Something went wrong. Please try again.
          </div>
        </div>
      </section>

      <!-- Tabs -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Tabs</h2>
          <p class="card-description">Tab navigation component</p>
        </div>
        
        <div>
          <div class="tabs">
            <button
              @click="activeTab = 'tab1'"
              :class="['tab', { active: activeTab === 'tab1' }]"
            >
              Tab 1
            </button>
            <button
              @click="activeTab = 'tab2'"
              :class="['tab', { active: activeTab === 'tab2' }]"
            >
              Tab 2
            </button>
            <button
              @click="activeTab = 'tab3'"
              :class="['tab', { active: activeTab === 'tab3' }]"
            >
              Tab 3
            </button>
            <button class="tab" disabled>
              Disabled
            </button>
          </div>
          
          <div class="mt-4 p-4 bg-preke-bg-surface rounded-lg">
            <p class="text-sm">Content for {{ activeTab }}</p>
          </div>
        </div>
      </section>

      <!-- Cards -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Cards</h2>
          <p class="card-description">Container components with headers and footers</p>
        </div>
        
        <div class="grid md:grid-cols-2 gap-4">
          <!-- Simple card -->
          <div class="card">
            <h3 class="text-lg font-semibold mb-2">Simple Card</h3>
            <p class="text-sm text-preke-text-dim">
              This is a basic card with some content inside it.
            </p>
          </div>
          
          <!-- Card with header and footer -->
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Card Title</h3>
              <p class="card-description">Card subtitle or description</p>
            </div>
            <p class="text-sm text-preke-text-dim">
              Main content area of the card.
            </p>
            <div class="card-footer">
              <button class="btn btn-primary text-sm">Action</button>
            </div>
          </div>
        </div>
      </section>

      <!-- Modals -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Modals</h2>
          <p class="card-description">Dialog and modal components</p>
        </div>
        
        <div class="flex flex-wrap gap-3">
          <button @click="openModal" class="btn btn-primary">
            Open Base Modal
          </button>
          <button @click="openConfirmDialog" class="btn btn-danger">
            Open Confirm Dialog
          </button>
        </div>
      </section>

      <!-- Spacing -->
      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Spacing Scale</h2>
          <p class="card-description">Consistent spacing units</p>
        </div>
        
        <div class="space-y-2">
          <div class="flex items-center gap-4">
            <span class="text-sm text-preke-text-dim w-20">0.5rem (8px)</span>
            <div class="h-2 bg-preke-gold rounded" style="width: 0.5rem;"></div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-preke-text-dim w-20">1rem (16px)</span>
            <div class="h-2 bg-preke-gold rounded" style="width: 1rem;"></div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-preke-text-dim w-20">1.5rem (24px)</span>
            <div class="h-2 bg-preke-gold rounded" style="width: 1.5rem;"></div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-preke-text-dim w-20">2rem (32px)</span>
            <div class="h-2 bg-preke-gold rounded" style="width: 2rem;"></div>
          </div>
        </div>
      </section>
    </div>

    <!-- Base Modal Example -->
    <BaseModal ref="modalRef" title="Example Modal" size="md">
      <div class="space-y-4">
        <p class="text-preke-text-dim">
          This is an example of the BaseModal component with a custom title and content.
        </p>
        <p class="text-sm text-preke-text-dim">
          You can add any content here including forms, images, or other components.
        </p>
      </div>
      
      <template #footer="{ close }">
        <button @click="close" class="btn">Cancel</button>
        <button @click="close" class="btn btn-primary">Confirm</button>
      </template>
    </BaseModal>

    <!-- Confirm Dialog Example -->
    <ConfirmDialog
      ref="confirmDialogRef"
      title="Confirm Action"
      message="Are you sure you want to perform this action? This cannot be undone."
      confirm-text="Yes, Continue"
      cancel-text="Cancel"
      :danger="true"
      @confirm="() => {}"
      @cancel="() => {}"
    />
  </div>
</template>

<style scoped>
.fleet-dashboard {
  @apply p-6;
}
</style>

