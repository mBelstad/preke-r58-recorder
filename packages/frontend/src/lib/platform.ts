/**
 * Platform detection and feature flags
 * Centralizes all platform-specific checks for cleaner component code
 */

// Runtime detection
export const platform = {
  // Environment detection
  isElectron: () => !!window.electronAPI?.isElectron,
  isWeb: () => !window.electronAPI?.isElectron,
  isDev: () => import.meta.env.DEV,
  
  // OS detection  
  isMacOS: () => navigator.platform.includes('Mac'),
  isWindows: () => navigator.platform.includes('Win'),
  isLinux: () => navigator.platform.includes('Linux'),
  
  // Feature flags - what capabilities are available
  features: {
    deviceDiscovery: () => !!window.electronAPI,
    tailscale: () => !!window.electronAPI,
    fileSystem: () => !!window.electronAPI,
    nativeMenus: () => !!window.electronAPI,
    pwa: () => !window.electronAPI?.isElectron,
  },
  
  // CSS class helpers
  getBodyClasses: () => {
    const classes: string[] = []
    // Use direct checks to avoid TDZ issues
    const isElectron = !!window.electronAPI?.isElectron
    const isWindows = navigator.platform.includes('Win')
    const isMacOS = navigator.platform.includes('Mac')
    if (isElectron) classes.push('electron-app')
    if (isWindows) classes.push('is-windows')
    if (isMacOS) classes.push('is-macos')
    return classes
  },
}

// Re-export isElectron for backward compatibility with existing imports
export const isElectron = platform.isElectron

