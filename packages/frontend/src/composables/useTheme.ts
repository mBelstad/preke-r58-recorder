/**
 * useTheme - Theme management composable
 * Handles light/dark mode switching with localStorage persistence
 * 
 * Uses lazy initialization to avoid TDZ issues in minified builds.
 */
import { ref, watch, onMounted, type Ref } from 'vue'

export type Theme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'preke-theme'

// Lazy singleton initialization to avoid TDZ issues
let _theme: Ref<Theme> | null = null
function getThemeRef(): Ref<Theme> {
  if (!_theme) {
    _theme = ref<Theme>('dark')
  }
  return _theme
}

/**
 * Apply theme to document
 */
function applyTheme(newTheme: Theme) {
  const root = document.documentElement
  if (newTheme === 'light') {
    root.setAttribute('data-theme', 'light')
  } else {
    root.removeAttribute('data-theme')
    // Ensure dark mode (default)
    root.setAttribute('data-theme', 'dark')
  }
}

/**
 * Load theme from localStorage
 */
function loadTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
  } catch (error) {
    console.warn('[Theme] Failed to load theme from localStorage:', error)
  }
  return 'dark' // Default to dark
}

/**
 * Save theme to localStorage
 */
function saveTheme(newTheme: Theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, newTheme)
  } catch (error) {
    console.warn('[Theme] Failed to save theme to localStorage:', error)
  }
}

export function useTheme() {
  // Get singleton ref (lazy initialization)
  const theme = getThemeRef()

  /**
   * Initialize theme on mount
   */
  function initializeTheme() {
    const savedTheme = loadTheme()
    theme.value = savedTheme
    applyTheme(savedTheme)
  }

  /**
   * Toggle between light and dark mode
   */
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  /**
   * Set theme explicitly
   */
  function setTheme(newTheme: Theme) {
    theme.value = newTheme
  }

  // Watch for theme changes and apply them
  watch(theme, (newTheme) => {
    applyTheme(newTheme)
    saveTheme(newTheme)
  }, { immediate: false })

  // Initialize on first use
  onMounted(() => {
    if (theme.value === 'dark' && !document.documentElement.hasAttribute('data-theme')) {
      initializeTheme()
    }
  })

  return {
    theme,
    toggleTheme,
    setTheme,
    initializeTheme
  }
}

