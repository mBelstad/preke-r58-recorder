/**
 * Platform detection and feature flags
 * Centralizes all platform-specific checks for cleaner component code
 */

// Helper functions (defined first to avoid TDZ issues)
const isElectronCheck = () => !!window.electronAPI?.isElectron
const isWebCheck = () => !window.electronAPI?.isElectron
const isDevCheck = () => import.meta.env.DEV
const isMacOSCheck = () => navigator.platform.includes('Mac')
const isWindowsCheck = () => navigator.platform.includes('Win')
const isLinuxCheck = () => navigator.platform.includes('Linux')

// Runtime detection
export const platform = {
  // Environment detection
  isElectron: isElectronCheck,
  isWeb: isWebCheck,
  isDev: isDevCheck,
  
  // OS detection  
  isMacOS: isMacOSCheck,
  isWindows: isWindowsCheck,
  isLinux: isLinuxCheck,
  
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
    const isElectron = isElectronCheck()
    const isWindows = isWindowsCheck()
    const isMacOS = isMacOSCheck()
    if (isElectron) classes.push('electron-app')
    if (isWindows) classes.push('is-windows')
    if (isMacOS) classes.push('is-macos')
    return classes
  },
}

// Re-export isElectron for backward compatibility with existing imports
export const isElectron = isElectronCheck

