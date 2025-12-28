# Testing Guide

> How to run tests, create test data, and debug issues.

## Table of Contents

1. [Test Strategy](#test-strategy)
2. [Running Tests](#running-tests)
3. [Writing Tests](#writing-tests)
4. [Test Data & Fixtures](#test-data--fixtures)
5. [Debugging Tips](#debugging-tips)
6. [CI/CD Integration](#cicd-integration)

---

## Test Strategy

### Test Pyramid

```
        ╱╲
       ╱  ╲
      ╱ E2E ╲         10% - Critical user journeys
     ╱────────╲
    ╱          ╲
   ╱ Integration ╲    30% - API contracts, service interactions
  ╱──────────────╲
 ╱                ╲
╱    Unit Tests    ╲  60% - Models, logic, stores, composables
╲──────────────────╱
```

### Coverage Goals

| Layer | Framework | Target | Location |
|-------|-----------|--------|----------|
| Unit (Backend) | pytest | 80% | `packages/backend/tests/` |
| Unit (Frontend) | Vitest | 70% | `packages/frontend/src/**/__tests__/` |
| Integration | pytest + httpx | 100% endpoints | `packages/backend/tests/integration/` |
| E2E | Playwright | Critical paths | `packages/frontend/e2e/` |

---

## Running Tests

### Backend Tests

```bash
cd packages/backend

# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific file
pytest tests/test_sessions_router.py -v

# Run specific test
pytest tests/test_sessions_router.py::TestStartRecording::test_start_recording_success -v

# Run by pattern
pytest tests/ -k "recording" -v

# Run with coverage
pytest tests/ --cov=r58_api --cov-report=html
open htmlcov/index.html

# Run only unit tests (fast)
pytest tests/ --ignore=tests/integration/ -v

# Run integration tests
pytest tests/integration/ -v

# Parallel execution
pytest tests/ -n auto
```

**Environment Variables:**

```bash
# For testing
export R58_JWT_SECRET=test-secret
export R58_DEVICE_ID=test-device-001
export R58_DEBUG=true
```

### Frontend Tests

```bash
cd packages/frontend

# Run unit tests (watch mode)
npm test

# Run once
npm test -- --run

# Run with coverage
npm test -- --run --coverage

# Run specific file
npm test -- src/stores/__tests__/recorder.test.ts

# Run by pattern
npm test -- --run -t "startRecording"

# Run with UI
npm test -- --ui
```

### E2E Tests

```bash
cd packages/frontend

# Install browsers (first time)
npx playwright install

# Run all E2E tests
npm run test:e2e

# Run specific file
npx playwright test e2e/recorder.spec.ts

# Run with UI mode
npm run test:e2e:ui

# Run in headed mode (see browser)
npx playwright test --headed

# Run specific browser
npx playwright test --project=chromium

# Debug mode
npx playwright test --debug
```

**Note:** E2E tests require the backend running:

```bash
# Terminal 1: Start backend
cd packages/backend
uvicorn r58_api.main:app --port 8000

# Terminal 2: Run E2E tests
cd packages/frontend
VITE_API_URL=http://localhost:8000 npm run test:e2e
```

### Device Smoke Tests

```bash
# On R58 device
./scripts/smoke-test.sh

# With recording test (requires HDMI input)
./scripts/smoke-test.sh --with-recording

# Verbose output
./scripts/smoke-test.sh --verbose
```

---

## Writing Tests

### Backend Unit Test Example

```python
# tests/test_my_feature.py
import pytest
from unittest.mock import AsyncMock


class TestMyFeature:
    """Tests for my feature"""
    
    def test_basic_functionality(self, client):
        """Test that basic request works"""
        response = client.get("/api/v1/my-feature/status")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_with_mock(self, client, mock_pipeline_client):
        """Test with mocked pipeline"""
        mock_pipeline_client.return_value.get_status = AsyncMock(
            return_value={"active": True}
        )
        
        response = client.get("/api/v1/my-feature/status")
        
        assert response.status_code == 200
        mock_pipeline_client.return_value.get_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_endpoint(self, async_client):
        """Test async endpoint"""
        response = await async_client.get("/api/v1/my-feature/")
        
        assert response.status_code == 200
```

### Frontend Unit Test Example

```typescript
// src/stores/__tests__/myStore.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMyStore } from '../myStore'

describe('MyStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('has correct initial state', () => {
    const store = useMyStore()
    
    expect(store.status).toBe('idle')
    expect(store.items).toHaveLength(0)
  })

  it('updates state on action', async () => {
    const store = useMyStore()
    
    await store.fetchItems()
    
    expect(store.status).toBe('loaded')
  })

  it('handles errors gracefully', async () => {
    // Mock fetch to fail
    vi.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('Network error'))
    
    const store = useMyStore()
    
    await store.fetchItems()
    
    expect(store.status).toBe('error')
  })
})
```

### E2E Test Example

```typescript
// e2e/my-feature.spec.ts
import { test, expect } from '@playwright/test'

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/my-feature')
  })

  test('displays content', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('My Feature')
  })

  test('can submit form', async ({ page }) => {
    await page.fill('[data-testid="name-input"]', 'Test Name')
    await page.click('[data-testid="submit-button"]')
    
    await expect(page.locator('.success-message')).toBeVisible()
  })

  test('handles API errors', async ({ page }) => {
    // Block API requests
    await page.route('**/api/v1/my-feature/**', route => 
      route.fulfill({ status: 500, body: 'Server Error' })
    )
    
    await page.click('[data-testid="load-button"]')
    
    await expect(page.locator('.error-message')).toBeVisible()
  })
})
```

---

## Test Data & Fixtures

### Backend Fixtures (conftest.py)

```python
# tests/conftest.py

@pytest.fixture
def client(app):
    """Sync test client"""
    return TestClient(app)

@pytest.fixture
async def async_client(app):
    """Async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_pipeline_client(monkeypatch):
    """Mock pipeline for unit tests"""
    mock = Mock()
    mock.get_recording_status = AsyncMock(return_value={"recording": False})
    monkeypatch.setattr("r58_api.media.pipeline_client.get_pipeline_client", lambda: mock)
    return mock

@pytest.fixture
def sample_session():
    """Sample recording session data"""
    return {
        "id": "test-session-123",
        "name": "Test Recording",
        "inputs": ["cam1", "cam2"],
        "started_at": datetime.now().isoformat(),
    }
```

### Frontend Fixtures (setup.ts)

```typescript
// src/test/setup.ts

export class MockWebSocket {
  static instances: MockWebSocket[] = []
  
  simulateMessage(data: object) {
    this.onmessage?.(new MessageEvent('message', { 
      data: JSON.stringify(data) 
    }))
  }
  
  static reset() {
    MockWebSocket.instances = []
  }
}

vi.stubGlobal('WebSocket', MockWebSocket)

export function mockFetchResponse(data: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  })
}
```

### Test Database

```python
@pytest.fixture
def test_db(tmp_path):
    """Create temporary test database"""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    return engine
```

---

## Debugging Tips

### Backend Debugging

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use pytest's built-in
pytest tests/test_my_file.py --pdb

# Print in tests
pytest tests/ -s  # Show stdout

# Verbose failures
pytest tests/ -vv --tb=long
```

### Frontend Debugging

```typescript
// Add debugger statement
debugger

// In test
console.log(wrapper.html())

// Vitest debug
npm test -- --run --reporter=verbose
```

### E2E Debugging

```bash
# Interactive debug mode
npx playwright test --debug

# Slow motion
npx playwright test --slow-mo=500

# Generate trace
npx playwright test --trace on

# View trace
npx playwright show-trace trace.zip

# Screenshot on failure
npx playwright test --screenshot=only-on-failure
```

### WebSocket Debugging

```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/api/v1/ws')
ws.onmessage = (e) => console.log('Received:', JSON.parse(e.data))
ws.send(JSON.stringify({ type: 'test', payload: {} }))
```

### API Debugging

```bash
# Verbose curl
curl -v http://localhost:8000/api/v1/health

# With timing
curl -w "@-" -o /dev/null -s "http://localhost:8000/api/v1/health" << 'EOF'
    time_total:  %{time_total}s\n
EOF

# Pretty print JSON
curl http://localhost:8000/api/v1/capabilities | jq
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/pr-checks.yml
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          cd packages/backend
          pip install -e .[dev]
          pytest tests/ -v --junitxml=results.xml
      - uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: packages/backend/results.xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: |
          cd packages/frontend
          npm ci
          npm test -- --run
```

### Running Tests in Docker

```bash
# Build test image
docker build -f docker/Dockerfile.test -t r58-tests .

# Run backend tests
docker run r58-tests pytest tests/ -v

# Run frontend tests
docker run r58-tests npm test -- --run
```

### Test Reports

```bash
# Generate JUnit report (for CI)
pytest tests/ --junitxml=report.xml

# Generate HTML report
pytest tests/ --html=report.html

# Coverage badge
pytest tests/ --cov=r58_api --cov-report=xml
# Upload coverage.xml to Codecov/Coveralls
```

---

## Quick Reference

### Common Commands

```bash
# Backend
pytest tests/ -v                 # All tests
pytest tests/ -k "test_name"     # By name
pytest tests/ --cov=r58_api      # Coverage

# Frontend
npm test                         # Watch mode
npm test -- --run               # Single run
npm run test:e2e                 # E2E tests

# Device
./scripts/smoke-test.sh          # Smoke tests
```

### Test Files Location

| Type | Location |
|------|----------|
| Backend Unit | `packages/backend/tests/test_*.py` |
| Backend Integration | `packages/backend/tests/integration/` |
| Frontend Unit | `packages/frontend/src/**/__tests__/` |
| Frontend E2E | `packages/frontend/e2e/` |
| Smoke Tests | `scripts/smoke-test.sh` |

