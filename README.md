# R58 Recorder/Mixer

> Professional multi-camera recording and live mixing solution for broadcast and AV production.

[![PR Checks](https://github.com/your-org/preke-r58-recorder/actions/workflows/pr-checks.yml/badge.svg)](https://github.com/your-org/preke-r58-recorder/actions)
[![Release](https://github.com/your-org/preke-r58-recorder/actions/workflows/release.yml/badge.svg)](https://github.com/your-org/preke-r58-recorder/releases)

## Features

- **Multi-Camera Recording** - Record up to 4 HDMI inputs simultaneously
- **Live Mixing** - VDO.ninja-powered video switching and composition
- **WebRTC Previews** - Low-latency WHEP streams for all inputs
- **PWA Interface** - Installable web app with kiosk mode support
- **Remote Access** - Control devices from anywhere via secure tunnels
- **Fleet Management** - Manage multiple R58 devices from one dashboard

---

## Quick Start

### Prerequisites

- **R58 Device**: Debian-based ARM device with HDMI capture
- **Development**: macOS/Linux with Python 3.11+ and Node.js 20+
- **Docker**: For containerized development

### 1. Clone & Setup

```bash
git clone https://github.com/your-org/preke-r58-recorder.git
cd preke-r58-recorder

# Backend setup
cd packages/backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Frontend setup
cd ../frontend
npm install
```

### 2. Configure Environment

```bash
# Create backend config
cat > packages/backend/.env << 'EOF'
R58_JWT_SECRET=change-this-in-production
R58_DEVICE_ID=dev-001
R58_DEBUG=true
R58_VDONINJA_ENABLED=true
EOF
```

### 3. Run Development Servers

```bash
# Terminal 1: Backend API
cd packages/backend
source .venv/bin/activate
uvicorn r58_api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend dev server
cd packages/frontend
npm run dev

# Terminal 3: (Optional) MediaMTX for WHEP streams
docker run -p 8889:8889 -p 9997:9997 bluenviron/mediamtx
```

### 4. Open the App

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         R58 Device                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Frontend   │    │   FastAPI    │    │ Pipeline Manager │  │
│  │  Vue3 + PWA  │◄──►│  Control API │◄──►│    (GStreamer)   │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         │                   │                     │             │
│         │                   ▼                     ▼             │
│         │            ┌──────────────┐    ┌──────────────────┐  │
│         │            │   SQLite DB  │    │     MediaMTX     │  │
│         │            │ (Sessions)   │    │  (WebRTC/WHEP)   │  │
│         │            └──────────────┘    └──────────────────┘  │
│         │                                        │             │
│         ▼                                        ▼             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    VDO.ninja (Local)                      │  │
│  │              Live Mixing & Scene Switching                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
preke-r58-recorder/
├── packages/
│   ├── backend/           # Python FastAPI + Pipeline Manager
│   │   ├── r58_api/       # Control plane (REST + WebSocket)
│   │   ├── pipeline_manager/  # Media plane (GStreamer control)
│   │   └── tests/         # pytest tests
│   └── frontend/          # Vue3 + TypeScript PWA
│       ├── src/
│       │   ├── views/     # Page components
│       │   ├── components/# UI components
│       │   ├── stores/    # Pinia state management
│       │   └── composables/# Vue composables
│       └── e2e/           # Playwright E2E tests
├── services/              # systemd unit files
├── docker/                # Dockerfiles and compose
├── scripts/               # Utility scripts
└── docs/                  # Documentation
```

---

## Development Commands

### Backend

```bash
cd packages/backend

# Run tests
pytest tests/ -v                        # All tests
pytest tests/ -k "recording" -v         # Filter by name
pytest tests/ --cov=r58_api             # With coverage

# Lint
ruff check .                            # Check
ruff check . --fix                      # Auto-fix

# Generate OpenAPI schema
python -c "from r58_api.main import create_app; create_app()"
```

### Frontend

```bash
cd packages/frontend

# Development
npm run dev                             # Dev server with HMR
npm run build                           # Production build
npm run preview                         # Preview production build

# Testing
npm test                                # Vitest watch mode
npm test -- --run                       # Single run
npm run test:e2e                        # Playwright E2E
npm run test:e2e:ui                     # Playwright UI mode

# Linting
npm run lint                            # ESLint
```

### Docker

```bash
# Full development environment
docker compose -f docker/docker-compose.dev.yml up

# Build images
docker build -f docker/Dockerfile.api -t r58-api packages/backend
docker build -f docker/Dockerfile.frontend -t r58-frontend packages/frontend
```

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Simple health check |
| GET | `/api/v1/health/detailed` | Detailed service status |
| GET | `/api/v1/capabilities` | Device capabilities manifest |
| GET | `/api/v1/recorder/status` | Current recorder status |
| POST | `/api/v1/recorder/start` | Start recording |
| POST | `/api/v1/recorder/stop` | Stop recording |
| WS | `/api/v1/ws` | Real-time event stream |

### Example: Start Recording

```bash
curl -X POST http://localhost:8000/api/v1/recorder/start \
  -H "Content-Type: application/json" \
  -d '{"name": "My Session", "inputs": ["cam1", "cam2"]}'
```

**Response:**
```json
{
  "session_id": "abc123",
  "name": "My Session",
  "started_at": "2024-12-28T10:00:00Z",
  "inputs": ["cam1", "cam2"],
  "status": "recording"
}
```

---

## Deployment

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for full deployment instructions.

### Quick Deploy to R58

```bash
# From development machine
./deploy-simple.sh
```

### Manual Deploy

```bash
# On R58 device
cd /opt/r58
git pull origin main
source venv/bin/activate
pip install -e packages/backend
cd packages/frontend && npm ci && npm run build
sudo systemctl restart r58-api r58-pipeline
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [START-HERE.md](docs/START-HERE.md) | Repo organization and contribution guide |
| [OPERATIONS.md](docs/OPERATIONS.md) | Deployment, services, and maintenance |
| [TESTING.md](docs/TESTING.md) | Test strategy and execution |
| [USER-GUIDE.md](docs/USER-GUIDE.md) | End-user workflows and troubleshooting |
| [SUPPORT-BUNDLE.md](docs/SUPPORT-BUNDLE.md) | Diagnostics and support data |
| [SMOKE_TEST_CHECKLIST.md](docs/SMOKE_TEST_CHECKLIST.md) | Pre-release checklist |

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and add tests
3. Run quality checks: `npm run lint && npm test && pytest`
4. Submit a pull request

See [START-HERE.md](docs/START-HERE.md) for detailed contribution guidelines.

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/preke-r58-recorder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/preke-r58-recorder/discussions)
- **Email**: support@example.com
