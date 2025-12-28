# UX + Performance Polish Plan for Professional Operators

This document outlines UI/UX improvements for R58, designed for professional broadcast and AV operators who need reliability, speed, and confidence during live production.

## Guiding Principles

1. **Trust through visibility** - Always show system state; never leave operators guessing
2. **Prevent accidents** - Safeguards for destructive actions, especially during recording
3. **Speed through shortcuts** - Keyboard-driven workflows for experienced operators
4. **Graceful degradation** - Show degraded states, not failures
5. **Latency awareness** - Make delays visible, not hidden

---

## 1. Latency and Health Indicators

### 1.1 Connection Status Badge (P1)

**Location:** StatusBar, top-right

**States:**
| State | Color | Label | Tooltip |
|-------|-------|-------|---------|
| Connected | Green | "Live" | "API connected, latency: 45ms" |
| Connecting | Yellow pulse | "Connecting..." | "Attempting to connect to API" |
| Degraded | Orange | "Slow (850ms)" | "High latency detected" |
| Disconnected | Red | "Offline" | "Connection lost. Reconnecting..." |

**Acceptance Criteria:**
- [ ] Ping API every 5 seconds, show round-trip latency
- [ ] Show latency value when > 200ms
- [ ] Pulse animation during reconnection attempts
- [ ] Click opens connection details modal

### 1.2 Recording Health Indicator (P1)

**Location:** RecorderView header, next to duration

**Shows:**
- Disk write speed (MB/s)
- Buffer status (OK / Warning / Critical)
- Frames dropped counter (if > 0)

**Acceptance Criteria:**
- [ ] Green: Writing at expected rate, buffer < 50%
- [ ] Yellow: Write speed low or buffer > 80%
- [ ] Red: Write failures or buffer overflow
- [ ] Tooltip shows detailed metrics

### 1.3 Input Signal Quality (P1)

**Location:** Each input card in InputGrid

**Shows:**
- Signal present/absent
- Resolution detected
- Framerate (with variance indicator)
- Audio levels (VU meter)

**Acceptance Criteria:**
- [ ] Green border: Signal stable at expected framerate (±1fps)
- [ ] Yellow border: Signal present but unstable
- [ ] Gray border: No signal
- [ ] Red overlay: Signal lost during recording

---

## 2. Error States and Feedback

### 2.1 Toast Notification System (P1)

**Types:**
| Type | Duration | Example |
|------|----------|---------|
| Success | 3s | "Recording started" |
| Warning | 5s | "Low disk space (2GB remaining)" |
| Error | Sticky | "Failed to start recording: Disk full" |
| Info | 4s | "Session saved to /recordings/..." |

**Acceptance Criteria:**
- [ ] Stack from bottom-right, max 3 visible
- [ ] Dismiss with X button or swipe
- [ ] Error toasts require manual dismiss
- [ ] Include "Retry" action for retryable errors

### 2.2 Inline Error States (P2)

**Recorder Controls:**
- Disabled state with reason tooltip
- "Cannot record: No inputs with signal"
- "Cannot stop: Already stopping..."

**Acceptance Criteria:**
- [ ] Disabled buttons show cursor-not-allowed
- [ ] Hover shows reason in tooltip
- [ ] Error state clears after 5s or user action

### 2.3 Full-Screen Error Overlay (P3)

**For critical failures:**
- API unreachable for > 30s
- Hardware failure detected
- Disk completely full

**Shows:**
- Error icon and message
- Suggested action
- "Retry" and "Get Support" buttons
- System diagnostics link

---

## 3. Keyboard Shortcuts

### 3.1 Global Shortcuts (P1)

| Shortcut | Action | Context |
|----------|--------|---------|
| `Space` | Toggle Recording | Recorder view |
| `Escape` | Cancel / Close modal | Any |
| `1-4` | Select input 1-4 | Recorder view |
| `M` | Toggle Mixer view | Any |
| `R` | Toggle Recorder view | Any |
| `?` | Show shortcuts help | Any |
| `Ctrl+S` | Quick save/export | Library view |

### 3.2 Mixer Shortcuts (P2)

| Shortcut | Action |
|----------|--------|
| `1-9` | Switch to scene 1-9 |
| `T` | Toggle transition |
| `A` | Auto-transition |
| `Tab` | Cycle through sources |
| `Enter` | Confirm selection |

### 3.3 Shortcuts Help Modal (P1)

**Trigger:** Press `?` or click help icon

**Shows:** Grouped list of all shortcuts with current context

**Acceptance Criteria:**
- [ ] Modal overlay with dark backdrop
- [ ] Grouped by view (Global, Recorder, Mixer)
- [ ] Shows disabled shortcuts with reason
- [ ] Dismisses on Escape or outside click

---

## 4. Safeguards

### 4.1 Recording Stop Confirmation (P1)

**Trigger:** Stop button during recording

**Dialog:**
```
Stop Recording?
You have been recording for 01:23:45.
This will finalize all files.

[Cancel]  [Stop Recording]
```

**Acceptance Criteria:**
- [ ] Danger-styled "Stop Recording" button
- [ ] Cannot be bypassed with keyboard
- [ ] 500ms delay before Stop button is clickable
- [ ] Shows recording duration in message

### 4.2 Accidental Navigation Prevention (P1)

**Trigger:** Navigate away during recording

**Shows:** Browser beforeunload warning + custom modal

**Acceptance Criteria:**
- [ ] Intercept all navigation (router + browser)
- [ ] "Recording in progress. Are you sure you want to leave?"
- [ ] Options: "Stay" (default) or "Leave and Stop Recording"

### 4.3 Session Name Requirement (P2)

**Option:** Configurable requirement for session names

**Behavior:**
- Prompt for session name before starting
- Suggest name based on date/time
- Remember last used naming pattern

### 4.4 Disk Space Pre-Check (P1)

**Trigger:** Before starting recording

**Shows warning if:**
- < 10GB free: Yellow warning, can proceed
- < 2GB free: Red warning, blocked from starting

**Acceptance Criteria:**
- [ ] Check disk space via API before start
- [ ] Show estimated recording time remaining
- [ ] Block start if critically low

---

## 5. Performance Optimizations

### 5.1 Lazy-Loaded Views (P2)

- Route-based code splitting (already done via Vue Router)
- Defer VDO.ninja iframe loading until mixer tab active
- Preload likely next views on idle

### 5.2 Debounced Updates (P1)

- Debounce rapid WebSocket events (combine updates within 100ms)
- Throttle DOM updates during recording (max 10fps for non-critical)
- Use CSS for animations, not JS

### 5.3 Memory Management (P2)

- Clear old recordings from state after navigation
- Limit stored heartbeat history (last 100)
- Dispose of unused video preview resources

---

## 6. Prioritized UI Improvements

### Priority 1 - Critical (Week 1)

| Item | Description | Acceptance Criteria |
|------|-------------|---------------------|
| Connection indicator | Show API connection status | Badge in StatusBar with latency |
| Toast notifications | Show success/error feedback | Stacked toasts, sticky errors |
| Stop confirmation | Prevent accidental stop | Modal with delay before confirm |
| Keyboard shortcuts | Space to toggle recording | Works from recorder view |
| Navigation guard | Warn when leaving during recording | Browser + router intercept |

### Priority 2 - High (Week 2)

| Item | Description | Acceptance Criteria |
|------|-------------|---------------------|
| Recording health | Show write speed/buffer | Health badge in header |
| Input signal quality | Visual feedback per input | Border colors + tooltip |
| Shortcuts help modal | Show all available shortcuts | Triggered with ? key |
| Error inline states | Disabled buttons with reason | Tooltips on disabled state |
| Disk space warning | Pre-check before recording | Warning dialog if low |

### Priority 3 - Medium (Week 3)

| Item | Description | Acceptance Criteria |
|------|-------------|---------------------|
| Mixer shortcuts | 1-9 for scenes, T for transition | Works in mixer view |
| Session naming | Prompt for name before start | Optional, configurable |
| Performance mode | Reduce UI updates during recording | Toggle in settings |
| Reconnection UI | Show reconnect attempts | Progress in status bar |

### Priority 4 - Polish (Week 4)

| Item | Description | Acceptance Criteria |
|------|-------------|---------------------|
| Sound effects | Optional audio feedback | Click, start, stop sounds |
| Haptic feedback | Vibration on mobile/tablet | For major actions |
| Theme variants | High contrast mode | Accessibility option |
| Touch optimizations | Larger touch targets | 44px minimum |

---

## 7. Accessibility Improvements

### 7.1 ARIA Labels (P2)

- All buttons have descriptive aria-label
- Recording status announced to screen readers
- Live regions for status changes

### 7.2 Focus Management (P2)

- Visible focus indicators (not just outline)
- Focus trap in modals
- Return focus after modal close

### 7.3 High Contrast Mode (P4)

- Toggle in settings
- Increase contrast ratios
- Larger text option

---

## 8. Implementation Order

```
Week 1: Foundation
├── Toast notification system
├── Connection status indicator
├── Stop recording confirmation
├── Keyboard shortcut system (global)
└── Navigation guard

Week 2: Recording Polish
├── Recording health indicator
├── Input signal quality UI
├── Shortcuts help modal
├── Disk space pre-check
└── Error state improvements

Week 3: Mixer + Performance
├── Mixer keyboard shortcuts
├── Session naming flow
├── Performance mode
└── Reconnection UI

Week 4: Accessibility + Polish
├── ARIA labels audit
├── Focus management
├── Sound/haptic feedback
└── Touch optimizations
```

---

## 9. Testing Checklist

### Manual Tests

- [ ] Start recording with Space key
- [ ] Stop confirmation appears and requires click
- [ ] Cannot navigate away during recording
- [ ] Toast appears on successful start/stop
- [ ] Error toast appears on API failure
- [ ] Connection indicator shows correct state
- [ ] Latency shows when > 200ms
- [ ] Disk warning appears when low
- [ ] Shortcuts modal opens with ?
- [ ] All shortcuts work as documented

### Automated Tests

- [ ] Toast component unit tests
- [ ] Keyboard shortcut handler tests
- [ ] Navigation guard tests
- [ ] Connection status logic tests
- [ ] Confirmation dialog tests

