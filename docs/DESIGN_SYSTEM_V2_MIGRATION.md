# Design System v2 - Migration Plan

## Overview

The new **Corporate Glassmorphism** design system is now documented and available at:
- **Style Guide**: `/#/style-guide-v2`
- **CSS File**: `packages/frontend/src/styles/design-system-v2.css`
- **Source Design**: Based on `DeviceSetupView.vue` (opening page & device discovery)

## Design Tokens Summary

### Color Palette

| Category | Variable | Value | Usage |
|----------|----------|-------|-------|
| **Brand** | `--preke-gold` | `#e0a030` | Primary accent, active states |
| | `--preke-gold-light` | `#f5c04a` | Hover states, gradients |
| | `--preke-gold-dark` | `#c48820` | Pressed states |
| **Background** | `--preke-bg-base` | `#0a0a0a` | Page background |
| | `--preke-bg-elevated` | `#121212` | Elevated surfaces |
| | `--preke-bg-surface` | `#1a1a1a` | Cards, panels |
| **Text** | `--preke-text-primary` | `#ffffff` | Headings, primary text |
| | `--preke-text-dim` | `#e8e0d0` | Body text |
| | `--preke-text-muted` | `#a8a8a8` | Secondary text |
| **Status** | `--preke-blue` | `#5a9fd4` | Info, links |
| | `--preke-green` | `#6db56d` | Success, connected |
| | `--preke-red` | `#d45a5a` | Danger, errors |
| | `--preke-amber` | `#f59e0b` | Warnings |

### Components

| Component | Class | Description |
|-----------|-------|-------------|
| **Glass Card** | `.glass-card` | Main container with blur, gradient, shadows |
| **Glass Panel** | `.glass-panel` | Lighter nested container |
| **Primary Button** | `.btn-v2--primary` | Gold gradient with shadow |
| **Success Button** | `.btn-v2--success` | Green gradient |
| **Danger Button** | `.btn-v2--danger` | Red gradient |
| **Ghost Button** | `.btn-v2--ghost` | Transparent with dashed border |
| **Glass Button** | `.btn-v2--glass` | Subtle glass background |
| **Icon Button** | `.btn-v2--icon` | Minimal icon-only button |
| **Input** | `.input-v2` | Dark input with subtle border |
| **Select** | `.select-v2` | Dropdown with custom arrow |
| **Badges** | `.badge-v2--*` | Status indicators |
| **Alerts** | `.alert-v2--*` | Notification boxes |
| **Device Item** | `.device-item-v2` | List item for devices |

---

## Migration Strategy

### Phase 1: Foundation (LOW RISK)
**Goal**: Import CSS without breaking existing functionality

1. **Add import to `style.css`**:
   ```css
   @import './styles/design-system-v2.css';
   ```

2. **Update Tailwind config** to use v2 tokens:
   ```js
   extend: {
     colors: {
       preke: {
         gold: 'var(--preke-gold)',
         'gold-light': 'var(--preke-gold-light)',
         // ... etc
       }
     }
   }
   ```

3. **Add body class** for v2 pages:
   ```html
   <body class="preke-v2">
   ```

### Phase 2: Component Migration (MEDIUM RISK)
**Goal**: Migrate individual components to v2 classes

#### Priority Order (Safest First):
1. ✅ **DeviceSetupView** - Already using v2 design
2. **StatusBar** - Simple, high visibility
3. **Sidebar** - Navigation, used everywhere
4. **Admin pages** - Low traffic, safe to experiment
5. **Library view** - Static content
6. **Recorder view** - Test carefully (video pipelines)
7. **Mixer view** - Test carefully (VDO.ninja iframes)

#### Migration Checklist Per Component:
- [ ] Update background colors to `--preke-bg-*`
- [ ] Update text colors to `--preke-text-*`
- [ ] Replace buttons with `.btn-v2--*` classes
- [ ] Replace cards with `.glass-card` / `.glass-panel`
- [ ] Replace badges with `.badge-v2--*`
- [ ] Update inputs to `.input-v2`
- [ ] Test all interactive states (hover, focus, active, disabled)
- [ ] Test responsive behavior
- [ ] Verify no visual regressions

### Phase 3: Page-by-Page Cleanup (CAREFUL)
**Goal**: Ensure consistent look across all pages

#### Off-Limits Files (DO NOT MODIFY):
- `packages/backend/**` - Video pipelines
- `packages/frontend/src/composables/useVdoNinja.ts` - VDO.ninja integration
- `packages/frontend/src/lib/vdoninja.ts` - VDO.ninja URL building
- Any file with WebRTC, WHEP, WHIP logic

#### Safe to Modify:
- `packages/frontend/src/views/*.vue` - View templates
- `packages/frontend/src/components/**/*.vue` - UI components
- `packages/frontend/src/styles/*.css` - Stylesheets
- `packages/frontend/tailwind.config.js` - Tailwind config

---

## Testing Checklist

### Before Each Migration:
- [ ] Create backup branch
- [ ] Note current visual appearance
- [ ] Test all functionality works

### After Each Migration:
- [ ] Visual comparison matches expected design
- [ ] All interactive elements work (buttons, inputs, links)
- [ ] No console errors
- [ ] Responsive design works
- [ ] Dark theme consistent
- [ ] Animations run smoothly

### Critical Path Testing:
- [ ] Device discovery works
- [ ] Recording start/stop works
- [ ] Video feeds display correctly
- [ ] Mixer controls work
- [ ] VDO.ninja iframes load

---

## Rollback Plan

If issues arise:
1. **Immediate**: Revert CSS import
2. **Per-component**: Git checkout specific file
3. **Full rollback**: `git revert` to pre-migration commit

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| DeviceSetupView | ✅ Complete | Source of v2 design |
| StyleGuideV2View | ✅ Complete | Documentation |
| StatusBar | ⏳ Pending | Phase 2 priority |
| Sidebar | ⏳ Pending | Phase 2 priority |
| StudioView | ⏳ Pending | |
| RecorderView | ⏳ Pending | Test carefully |
| MixerView | ⏳ Pending | Test carefully |
| LibraryView | ⏳ Pending | |
| AdminView | ⏳ Pending | |
| GuestView | ⏳ Pending | |

---

## Next Steps

1. **Review this plan** with the team
2. **Start Phase 1** - Add CSS import
3. **Migrate StatusBar** as first component test
4. **Iterate** based on feedback

