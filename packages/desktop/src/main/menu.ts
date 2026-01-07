/**
 * Application menu for R58 Studio Desktop
 */

import { Menu, app, shell, MenuItemConstructorOptions } from 'electron'
import { reloadMainWindow, toggleDevTools, showDeviceSetup, getMainWindow } from './window'
import { log } from './logger'

// Development mode detection
const isDev = !app.isPackaged

/**
 * Create and set the application menu
 */
export function createApplicationMenu(): void {
  const template = getMenuTemplate()
  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
  log.info('Application menu created')
}

/**
 * Get the menu template based on platform
 */
function getMenuTemplate(): MenuItemConstructorOptions[] {
  const isMac = process.platform === 'darwin'

  const template: MenuItemConstructorOptions[] = [
    // App menu (macOS only)
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' as const },
        { type: 'separator' as const },
        {
          label: 'Devices...',
          accelerator: 'CmdOrCtrl+,',
          click: () => showDeviceSetup()
        },
        { type: 'separator' as const },
        { role: 'services' as const },
        { type: 'separator' as const },
        { role: 'hide' as const },
        { role: 'hideOthers' as const },
        { role: 'unhide' as const },
        { type: 'separator' as const },
        { role: 'quit' as const }
      ]
    }] : []),

    // File menu (Windows/Linux)
    ...(!isMac ? [{
      label: 'File',
      submenu: [
        {
          label: 'Devices...',
          accelerator: 'CmdOrCtrl+,',
          click: () => showDeviceSetup()
        },
        { type: 'separator' as const },
        { role: 'quit' as const }
      ]
    }] : []),

    // Edit menu (for copy/paste)
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' as const },
        { role: 'redo' as const },
        { type: 'separator' as const },
        { role: 'cut' as const },
        { role: 'copy' as const },
        { role: 'paste' as const },
        { role: 'selectAll' as const }
      ]
    },

    // View menu
    {
      label: 'View',
      submenu: [
        { 
          role: 'reload' as const,
          accelerator: 'CmdOrCtrl+R',
          click: () => reloadMainWindow()
        },
        { 
          role: 'forceReload' as const,
          accelerator: 'CmdOrCtrl+Shift+R'
        },
        // DevTools only in development
        ...(isDev ? [
          { type: 'separator' as const },
          { 
            label: 'Toggle Developer Tools',
            accelerator: isMac ? 'Alt+Cmd+I' : 'Ctrl+Shift+I',
            click: () => toggleDevTools()
          }
        ] : []),
        { type: 'separator' as const },
        { role: 'resetZoom' as const },
        { role: 'zoomIn' as const },
        { role: 'zoomOut' as const },
        { type: 'separator' as const },
        { role: 'togglefullscreen' as const }
      ]
    },

    // Window menu
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' as const },
        { role: 'zoom' as const },
        ...(isMac ? [
          { type: 'separator' as const },
          { role: 'front' as const },
          { type: 'separator' as const },
          { role: 'window' as const }
        ] : [
          { role: 'close' as const }
        ])
      ]
    },

    // Help menu
    {
      role: 'help' as const,
      submenu: [
        {
          label: 'Preke Studio Documentation',
          click: async () => {
            await shell.openExternal('https://github.com/itagenten/preke-r58-recorder')
          }
        },
        {
          label: 'Report Issue',
          click: async () => {
            await shell.openExternal('https://github.com/itagenten/preke-r58-recorder/issues')
          }
        },
        { type: 'separator' as const },
        {
          label: 'Export Support Bundle...',
          click: async () => {
            const win = getMainWindow()
            if (win) {
              win.webContents.send('export-support-bundle')
            }
          }
        },
        { type: 'separator' as const },
        {
          label: `Version ${app.getVersion()}`,
          enabled: false
        }
      ]
    }
  ]

  return template
}

/**
 * Show context menu for right-click
 */
export function showContextMenu(): void {
  const template: MenuItemConstructorOptions[] = [
    { role: 'reload' },
    ...(isDev ? [{ role: 'toggleDevTools' as const }] : []),
    { type: 'separator' as const },
    { role: 'cut' as const },
    { role: 'copy' as const },
    { role: 'paste' as const },
  ]
  
  const menu = Menu.buildFromTemplate(template)
  menu.popup()
}

