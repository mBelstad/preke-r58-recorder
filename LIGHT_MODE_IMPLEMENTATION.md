# Light Mode Implementation Guide

## Project Overview

**Project Name:** Preke Studio (R58 Recorder)  
**Type:** Desktop/Web Application (Electron + Vue 3)  
**Purpose:** Remote control application for R58 recording devices with mixer and recorder modes

## Project Structure

```
preke-r58-recorder/
├── packages/
│   ├── frontend/          # Vue 3 + TypeScript frontend
│   │   ├── src/
│   │   │   ├── components/ # Vue components
│   │   │   ├── views/      # Page views
│   │   │   ├── styles/     # CSS files
│   │   │   ├── stores/     # Pinia stores
│   │   │   └── composables/# Vue composables
│   │   └── package.json
│   └── desktop/           # Electron wrapper
│       └── package.json
└── package.json           # Root workspace config
```

## Current Theme System

### Design System Location
**File:** `packages/frontend/src/styles/preke-design-system.css`

### Key Information:
1. **Light mode CSS already exists!** The design system has light mode variables defined under `[data-theme="light"]` selector (lines 168-219)
2. **Dark mode is default** - defined in `:root` and `[data-theme="dark"]` (lines 19-161)
3. **CSS Custom Properties** - All colors use CSS variables (--preke-*)
4. **Theme switching mechanism** - Uses `data-theme` attribute on root element

### Current Theme Variables:

**Dark Mode (default):**
- Backgrounds: `--preke-bg-base: #0a0a0a`, `--preke-bg-elevated: #121212`
- Text: `--preke-text: #ffffff`, `--preke-text-muted: #a8a8a8`
- Gold accent: `--preke-gold: #e0a030`

**Light Mode (already defined):**
- Backgrounds: `--preke-bg-base: #f5f5f5`, `--preke-bg-elevated: #ffffff`
- Text: `--preke-text: #1a1a1a`, `--preke-text-muted: #666666`
- Gold accent: `--preke-gold: #c48820` (darker for contrast)

## Settings Management

### Current Settings Storage
**File:** `packages/frontend/src/components/admin/SettingsPanel.vue`

**Storage Method:**
- Web: `localStorage` with key `'preke-settings'`
- Desktop: Electron store (via `window.electronAPI`)

**Current Settings Structure:**
```typescript
{
  deviceName: string
  vdoRoom: string
  autoCleanup: boolean
  cleanupDays: number
}
```

## Implementation Plan

### Step 1: Create Theme Composable
**File:** `packages/frontend/src/composables/useTheme.ts`

Create a composable to manage theme state:
- Read/write theme preference from localStorage
- Apply `data-theme` attribute to document root
- Provide reactive theme state
- Handle Electron environment if needed

### Step 2: Add Theme Toggle to Settings
**File:** `packages/frontend/src/components/admin/SettingsPanel.vue`

Add a toggle switch in the settings panel:
- Use the `useTheme` composable
- Save preference to localStorage
- Update existing settings save/load functions

### Step 3: Initialize Theme on App Start
**File:** `packages/frontend/src/main.ts` or `App.vue`

Initialize theme from localStorage when app loads:
- Check for saved theme preference
- Apply theme before first render (prevent flash)

### Step 4: Add Toggle to Top Bar (Optional)
**File:** `packages/frontend/src/components/layout/StatusBarV2.vue`

Add a quick theme toggle button in the top bar for easy access.

## Technical Details

### CSS Theme Switching
The theme is switched by setting `data-theme` attribute on `<html>` or `<body>`:

```javascript
// Dark mode (default)
document.documentElement.setAttribute('data-theme', 'dark')
// or remove attribute

// Light mode
document.documentElement.setAttribute('data-theme', 'light')
```

### Storage Key
Use consistent key: `'preke-theme'` or add to existing `'preke-settings'` object.

### Default Theme
- Default: `'dark'` (current default)
- User preference: Store in localStorage
- System preference: Could detect via `prefers-color-scheme` media query (optional enhancement)

## Components That May Need Attention

### Background Elements
- **StudioView.vue** - Has animated background shapes, soundwaves, purple lights
- **DesignProposalsView.vue** - Various background experiments
- May need to adjust opacity/colors for light mode

### Glass Effects
- Many components use glassmorphism (`backdrop-filter: blur`)
- Light mode already has adjusted glass variables
- Should work automatically via CSS variables

### Images/Logos
- Check if any logos need light/dark variants
- SVG logos should adapt via CSS filters if needed

## Testing Checklist

- [ ] Toggle works in web app
- [ ] Toggle works in Electron app
- [ ] Theme persists after app restart
- [ ] All pages render correctly in light mode
- [ ] Background animations look good in light mode
- [ ] Glass effects work in light mode
- [ ] Text contrast is sufficient
- [ ] Gold accent colors are visible
- [ ] No flash of wrong theme on load

## Build Commands

```bash
# Development (web)
cd packages/frontend && npm run dev

# Development (Electron)
cd packages/desktop && npm run dev

# Build all
cd packages/desktop && npm run test:build-all
```

## Key Files Reference

1. **Design System:** `packages/frontend/src/styles/preke-design-system.css`
2. **Settings Panel:** `packages/frontend/src/components/admin/SettingsPanel.vue`
3. **Main App:** `packages/frontend/src/App.vue` or `main.ts`
4. **Top Bar:** `packages/frontend/src/components/layout/StatusBarV2.vue`
5. **Home Page:** `packages/frontend/src/views/StudioView.vue`

## Notes

- The light mode CSS is already complete and well-designed
- Only need to implement the toggle mechanism
- Consider adding smooth transitions when switching themes
- May want to add a keyboard shortcut (e.g., Cmd/Ctrl + Shift + T)

