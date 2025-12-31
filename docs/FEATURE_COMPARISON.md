# Feature Comparison: Vanilla App vs Vue App

## Screenshots
All screenshots of the old vanilla app are saved in `/docs/old-app-screenshots/`:
- `old-app-01-studio.png` - Studio/Multiview with recording controls
- `old-app-02-library.png` - Recording library with sessions
- `old-app-03-mixer.png` - VDO.ninja mixer with camera-to-slot mapper
- `old-app-04-graphics.png` - Graphics/Lower thirds editor
- `old-app-05-guests.png` - Guest management and invite links
- `old-app-06-settings.png` - Settings page
- `old-app-07-guest-portal.png` - Guest join page (standalone)

---

## Feature Matrix

| Feature | Vanilla App | Vue App | Notes |
|---------|-------------|---------|-------|
| **Studio/Recorder** |
| 2x2 Multiview | ✅ | ✅ | Both have 4-camera grid |
| WebRTC (WHEP) preview | ✅ | ✅ | Vue uses InputPreview component |
| HLS fallback | ✅ | ❌ | Vue only uses WebRTC |
| Click-to-fullscreen camera | ✅ | ❌ | Not in Vue |
| Recording start/stop | ✅ | ✅ | Both work |
| Recording duration timer | ✅ | ✅ | |
| Stream mode selector (latency) | ✅ | ❌ | Low/Balanced/Stable modes |
| Camera status badges | ✅ | ✅ | |
| Disk space display | ✅ | ❌ | Not shown in Vue |
| **Library** |
| Session listing | ✅ | ✅ | |
| Date grouping | ✅ | ❌ | Vanilla groups by date |
| Session metadata (duration, size) | ✅ | ✅ | |
| Video thumbnails | ✅ | ⚠️ | Vue uses icons, vanilla loads real thumbs |
| Play video inline | ✅ | ✅ | |
| Download recordings | ✅ | ✅ | |
| Copy session ID | ✅ | ❌ | |
| Download metadata JSON | ✅ | ❌ | |
| Edit session name | ✅ | ✅ | Vue stores locally |
| **Mixer** |
| Active sources list | ✅ | ✅ | Shows cameras with resolution |
| Source status (active/inactive) | ✅ | ✅ | |
| Summary stats (cameras, speakers) | ✅ | ❌ | Vanilla shows counts |
| **Camera-to-Slot Mapper** | ✅ | ❌ | **MISSING IN VUE** |
| Open VDO.ninja mixer | ✅ | ✅ | |
| Open Director | ✅ | ✅ | |
| Copy mixer URL | ✅ | ❌ | |
| Scene URL display | ✅ | ❌ | |
| Copy scene URL | ✅ | ❌ | |
| Start camera streaming | ✅ | ✅ | |
| VDO.ninja iframe embed | ❌ | ✅ | Vue embeds, vanilla opens new tab |
| Local/cloud recording controls | ❌ | ✅ | Only in Vue |
| **Graphics** |
| Lower thirds editor | ✅ | ❌ | **MISSING IN VUE** |
| Template selection | ✅ | ❌ | Simple/Full/Minimal |
| Show/Hide lower third | ✅ | ❌ | |
| Media library | ✅ | ❌ | |
| Presentations | ✅ | ❌ | |
| Graphics editor | ✅ | ❌ | |
| **Guests** |
| Guest invite link | ✅ | ✅ | Via GuestView |
| Director link | ✅ | ✅ | |
| Guest slots display | ✅ | ❌ | Shows 4 empty slots |
| Copy invite links | ✅ | ✅ | |
| Open links in new tab | ✅ | ✅ | |
| **Guest Portal** |
| Camera/mic preview | ✅ | ✅ | |
| Name input | ✅ | ✅ | |
| Device selection | ✅ | ✅ | |
| Join studio button | ✅ | ✅ | |
| **Settings/Admin** |
| Device info | ✅ | ✅ | Vue has more details |
| Mode switching (Recorder/Mixer) | ❌ | ✅ | Only in Vue |
| System status | ❌ | ✅ | CPU, services, pipelines |
| Logs viewer | ❌ | ✅ | |
| Fleet management | ❌ | ✅ | |
| Developer tools link | ✅ | ❌ | |

---

## Key Features Missing in Vue App

### 1. Camera-to-Slot Mapper ⭐ HIGH PRIORITY
The vanilla app has a full camera-to-slot mapper that assigns cameras (cam0-cam3) and guests to VDO.ninja mixer slots (0-9). This is critical for controlling which source appears in which position in the mixer.

**API Endpoints:**
- `GET /api/vdoninja/mapping` - Get current mappings
- `POST /api/vdoninja/mapping` - Save mappings
- `POST /api/vdoninja/mapping/reset` - Reset to defaults

### 2. Graphics/Lower Thirds ⭐ HIGH PRIORITY
Full graphics overlay system with:
- Lower third templates (Simple, Full, Minimal)
- Name/Title input
- Show/Hide controls
- Media library
- Presentations
- Graphics editor

**API Endpoints:**
- `GET /api/graphics/lower_third`
- `POST /api/graphics/lower_third`
- `GET /api/graphics/templates`

### 3. Scene URL & Copy Functions
- Display and copy the Scene URL for OBS
- Copy Mixer URL button

### 4. Stream Mode Selector
Low latency (~1s), Balanced (~2s), Stable (~10s) modes for preview streams.

### 5. Click-to-Fullscreen Camera
In the multiview, clicking a camera expands it to full size.

### 6. Better Library Organization
- Group recordings by date
- Show duration, size for each file
- Copy Session ID button
- Download metadata JSON

---

## What Vue App Does Better

1. **Modern Component Architecture** - Reusable Vue components, Pinia stores
2. **Better UI/UX** - Glassmorphism, animations, responsive design
3. **Embedded VDO.ninja** - Full mixer in iframe instead of popup
4. **Local/Cloud Recording** - VDO.ninja recording controls
5. **System Monitoring** - CPU, memory, services, pipelines
6. **Mode Switching** - Switch between Recorder/Mixer modes
7. **Device Discovery** - Auto-discover R58 devices (Electron)
8. **Logs Viewer** - View system logs
9. **Fleet Management** - Multi-device support (future)

---

## Lessons from Vanilla App

### Code Organization
- Each section (studio, mixer, guests) is a separate JS file
- State is managed in module-level objects
- Functions are exposed globally via `window.`

### UI Patterns
- CSS custom properties for theming
- Grid layouts for responsive design
- Status badges with color coding
- Toast notifications for feedback
- Loading states with spinners

### API Usage
- All API calls use relative URLs (`/api/...`)
- Polling intervals for live updates (15s typical)
- Error handling with fallbacks
- URL generation via API endpoints

### Streaming
- WebRTC (WHEP) as primary
- HLS as fallback for compatibility
- Stream mode affects buffer size

---

## Migration Plan

### Phase 1: Serve Vue App (This PR)
1. Backup vanilla app to `/static/legacy/`
2. Configure nginx/FastAPI to serve Vue at `/static/app.html`
3. Test basic functionality

### Phase 2: Add Missing Features
1. Camera-to-Slot Mapper component
2. Graphics/Lower Thirds integration
3. Scene URL display and copy
4. Stream mode selector
5. Click-to-fullscreen for cameras

### Phase 3: Polish
1. Better library organization (date grouping)
2. Session metadata buttons
3. Guest slots display
4. Developer tools link

---

## Files to Migrate

### Keep (serve from legacy or integrate):
- `/static/guest.html` → Keep as standalone guest portal
- `/static/graphics.html` → Integrate into Vue or keep as iframe
- `/static/library.html` → Already in Vue, enhance it
- `/static/broadcast_graphics.html` → OBS overlay, keep as-is
- `/static/editor.html` → Keep for advanced graphics editing

### Can Replace:
- `/static/app.html` → Replace with Vue
- `/static/studio.html` → Replaced by Vue RecorderView
- `/static/mediamtx_mixer.html` → Replaced by Vue MixerView

### Utility Pages (keep):
- `/static/camera-preview.html` → WebRTC test page
- `/static/test_cameras.html` → Camera testing
- `/static/dev.html` → Developer tools

