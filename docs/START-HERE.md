# Start Here - Developer Onboarding

> Everything you need to understand the R58 codebase and contribute safely.

## Table of Contents

1. [Repository Organization](#repository-organization)
2. [Architecture Overview](#architecture-overview)
3. [Key Concepts](#key-concepts)
4. [Adding Features Safely](#adding-features-safely)
5. [Code Style & Conventions](#code-style--conventions)
6. [Common Tasks](#common-tasks)

---

## Repository Organization

```
preke-r58-recorder/
│
├── packages/                      # Monorepo packages
│   ├── backend/                   # Python backend
│   │   ├── r58_api/              # FastAPI control plane
│   │   │   ├── control/          # REST endpoints by domain
│   │   │   │   ├── auth/         # JWT authentication
│   │   │   │   ├── devices/      # Device capabilities
│   │   │   │   ├── sessions/     # Recording sessions
│   │   │   │   ├── fleet/        # Multi-device management
│   │   │   │   └── vdoninja.py   # VDO.ninja URL builder
│   │   │   ├── media/            # Pipeline manager client
│   │   │   ├── realtime/         # WebSocket handlers
│   │   │   ├── observability/    # Health, metrics, support
│   │   │   ├── models/           # SQLModel database models
│   │   │   ├── db/               # Database setup
│   │   │   └── static/           # Static assets (CSS for VDO.ninja)
│   │   ├── pipeline_manager/     # GStreamer pipeline control (separate process)
│   │   │   ├── main.py           # Entry point
│   │   │   ├── state.py          # Persistent state
│   │   │   └── ipc.py            # Unix socket IPC
│   │   └── tests/                # pytest tests
│   │       ├── conftest.py       # Shared fixtures
│   │       ├── test_*.py         # Unit tests
│   │       └── integration/      # Integration tests
│   │
│   └── frontend/                  # Vue3 TypeScript PWA
│       ├── src/
│       │   ├── views/            # Page-level components
│       │   ├── components/       # Reusable UI components
│       │   │   ├── layout/       # App shell, sidebar, status bar
│       │   │   ├── recorder/     # Recorder-specific components
│       │   │   ├── mixer/        # Mixer-specific components
│       │   │   ├── admin/        # Admin/dev tools components
│       │   │   └── shared/       # Shared components
│       │   ├── stores/           # Pinia state stores
│       │   ├── composables/      # Vue composables (hooks)
│       │   ├── lib/              # Utility libraries
│       │   ├── router/           # Vue Router config
│       │   └── api/              # Generated API client
│       ├── e2e/                  # Playwright E2E tests
│       └── public/               # Static assets
│
├── services/                      # systemd unit files
│   ├── r58-api.service
│   ├── r58-pipeline.service
│   └── r58-mediamtx.service
│
├── docker/                        # Container configs
│   ├── Dockerfile.api
│   ├── Dockerfile.frontend
│   └── docker-compose.dev.yml
│
├── scripts/                       # Utility scripts
│   ├── generate-client.sh        # OpenAPI -> TypeScript
│   └── smoke-test.sh             # Device smoke tests
│
├── docs/                          # Documentation
├── openapi/                       # Generated OpenAPI schema
└── .github/workflows/             # CI/CD pipelines
```

---

## Architecture Overview

### Control Plane vs Media Plane

The system is split into two planes:

| Aspect | Control Plane | Media Plane |
|--------|--------------|-------------|
| **Process** | `r58-api` (FastAPI) | `r58-pipeline` (Python + GStreamer) |
| **Purpose** | REST API, WebSocket, Auth | Video encoding, file writing |
| **Language** | Python (async) | Python (sync, GStreamer) |
| **Communication** | HTTP/WS to clients | Unix socket IPC from API |
| **State** | SQLite database | JSON file persistence |

**Why separate?** Heavy media operations would block async request handlers. The pipeline manager runs in its own process with robust state recovery.

### Data Flow

```
Browser ──HTTP/WS──► FastAPI ──IPC──► Pipeline Manager ──GStreamer──► Files
                         │                    │
                         ▼                    ▼
                     SQLite              MediaMTX (WHEP)
                    (sessions)           (previews)
```

### Key Files to Understand

| File | Purpose |
|------|---------|
| `r58_api/main.py` | FastAPI app factory, router registration |
| `r58_api/config.py` | Pydantic settings, environment variables |
| `r58_api/control/sessions/router.py` | Recording start/stop endpoints |
| `r58_api/realtime/events.py` | WebSocket event schema |
| `pipeline_manager/state.py` | Recording state persistence |
| `pipeline_manager/ipc.py` | IPC server implementation |
| `frontend/src/stores/recorder.ts` | Recorder state machine |
| `frontend/src/composables/useWebSocket.ts` | WebSocket client |

---

## Key Concepts

### 1. Capabilities-Driven UI

The UI adapts based on device capabilities:

```typescript
// Frontend checks capabilities and shows/hides features
const caps = await fetch('/api/v1/capabilities')
if (caps.mixer_available) {
  showMixerTab()
}
```

**To add a new capability:**
1. Add field to `DeviceCapabilities` model in `capabilities.py`
2. Update detection logic
3. Use capability in frontend

### 2. WebSocket Event Schema

All events follow a versioned schema:

```python
class BaseEvent(BaseModel):
    v: int = 1              # Schema version
    type: EventType         # Event type enum
    ts: datetime            # Timestamp
    seq: int                # Sequence number
    device_id: str          # Source device
    payload: dict | None    # Event-specific data
```

**To add a new event:**
1. Add to `EventType` enum
2. Create factory method if needed
3. Handle in frontend `handleEvent()`

### 3. Recording State Machine

```
     ┌──────────┐
     │   IDLE   │◄────────────────────┐
     └────┬─────┘                     │
          │ start_recording()         │ stop_recording()
          ▼                           │
     ┌──────────┐                     │
     │ STARTING │                     │
     └────┬─────┘                     │
          │ pipeline_started          │
          ▼                           │
     ┌──────────┐                     │
     │RECORDING │─────────────────────┘
     └──────────┘
          │ stop_recording()
          ▼
     ┌──────────┐
     │ STOPPING │
     └────┬─────┘
          │ pipeline_stopped
          ▼
       (IDLE)
```

---

## Adding Features Safely

### Checklist for New Features

- [ ] Does it touch the API? Update OpenAPI schema and regenerate client
- [ ] Does it need new state? Add to appropriate Pinia store
- [ ] Does it need persistence? Add SQLModel or state.py changes
- [ ] Does it affect recording? Test with actual files
- [ ] Does it work offline? Consider PWA caching
- [ ] Is it device-specific? Add capability flag

### Step-by-Step: Adding a New API Endpoint

1. **Create router file or add to existing:**

```python
# r58_api/control/my_feature/router.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/my-feature", tags=["MyFeature"])

class MyRequest(BaseModel):
    name: str

class MyResponse(BaseModel):
    id: str
    name: str

@router.post("/", response_model=MyResponse)
async def create_my_feature(request: MyRequest):
    return MyResponse(id="123", name=request.name)
```

2. **Register in main.py:**

```python
from .control.my_feature.router import router as my_feature_router
app.include_router(my_feature_router)
```

3. **Add tests:**

```python
# tests/test_my_feature.py
def test_create_my_feature(client):
    response = client.post("/api/v1/my-feature/", json={"name": "Test"})
    assert response.status_code == 200
    assert response.json()["name"] == "Test"
```

4. **Regenerate API client:**

```bash
cd packages/frontend
npm run generate-api
```

5. **Use in frontend:**

```typescript
import { MyFeatureService } from '@/api'

const result = await MyFeatureService.createMyFeature({ name: 'Test' })
```

### Step-by-Step: Adding a New Vue Component

1. **Create component:**

```vue
<!-- components/my-feature/MyComponent.vue -->
<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
</script>

<template>
  <button @click="count++">Count: {{ count }}</button>
</template>
```

2. **Add to view or parent component:**

```vue
<script setup lang="ts">
import MyComponent from '@/components/my-feature/MyComponent.vue'
</script>

<template>
  <MyComponent />
</template>
```

3. **Add tests:**

```typescript
// components/my-feature/__tests__/MyComponent.test.ts
import { mount } from '@vue/test-utils'
import MyComponent from '../MyComponent.vue'

test('increments count', async () => {
  const wrapper = mount(MyComponent)
  await wrapper.find('button').trigger('click')
  expect(wrapper.text()).toContain('Count: 1')
})
```

---

## Code Style & Conventions

### Python

- **Formatter**: ruff (line length 100)
- **Type hints**: Required for public functions
- **Async**: Use async/await for I/O operations
- **Naming**: snake_case for functions/variables, PascalCase for classes

```python
# Good
async def get_recording_status(session_id: str) -> RecordingStatus:
    ...

# Bad
def GetRecordingStatus(sessionId):
    ...
```

### TypeScript/Vue

- **Style**: ESLint + Prettier (via editor)
- **Composition API**: Always use `<script setup>`
- **Naming**: camelCase for variables, PascalCase for components
- **Props**: Use TypeScript interfaces

```vue
<!-- Good -->
<script setup lang="ts">
interface Props {
  sessionId: string
  isActive?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isActive: false
})
</script>
```

### Git Commits

```
feat: add session export functionality
fix: resolve WebSocket reconnection loop
docs: update API reference
test: add integration tests for storage
refactor: simplify pipeline state machine
```

---

## Common Tasks

### Regenerate API Client

When backend endpoints change:

```bash
cd packages/backend
python -c "from r58_api.main import create_app; create_app()"  # Generates openapi.json

cd ../frontend
npm run generate-api
```

### Run All Quality Checks

```bash
# Backend
cd packages/backend
ruff check .
pytest tests/ -v

# Frontend
cd packages/frontend
npm run lint
npm test -- --run
npm run build
```

### Test on Real Device

```bash
# Deploy to R58
./deploy-simple.sh

# Run smoke tests on device
./connect-r58-frp.sh
# Then on device:
/opt/r58/scripts/smoke-test.sh --with-recording
```

### Debug WebSocket Issues

```javascript
// In browser console
localStorage.debug = 'r58:*'  // Enable debug logging

// Or check WebSocket frames in DevTools > Network > WS
```

### Check Service Logs

```bash
# On R58 device
sudo journalctl -u r58-api -f        # API logs
sudo journalctl -u r58-pipeline -f   # Pipeline logs
sudo journalctl -u mediamtx -f       # MediaMTX logs
```

---

## Getting Help

1. **Search existing docs** in `/docs` folder
2. **Check GitHub Issues** for similar problems
3. **Ask in team chat** with reproduction steps
4. **Create an issue** if it's a bug

Welcome to the team!

