# R58 WebSocket Relay Service

WebSocket signaling relay that bridges R58 devices with remote controllers.

## Architecture

```
R58 Device (Venue)
    ↓ WebSocket: wss://relay.r58.itagenten.no/unit/{unit-id}
Relay Server (Coolify)
    ↓ WebSocket: wss://relay.r58.itagenten.no/control/{unit-id}
Remote Controller (Browser)
```

## Endpoints

### WebSocket: /unit/{unit-id}
For R58 devices to connect and publish their signaling

**Example:**
```javascript
const ws = new WebSocket('wss://relay.r58.itagenten.no/unit/r58-001');
```

### WebSocket: /control/{unit-id}
For remote controllers to connect and view/control R58

**Example:**
```javascript
const ws = new WebSocket('wss://relay.r58.itagenten.no/control/r58-001');
```

### HTTP GET /health
Health check endpoint

**Response:**
```json
{
  "status": "ok",
  "service": "r58-relay",
  "units": 5,
  "controllers": 12
}
```

## Message Flow

1. R58 connects to `/unit/{id}` and keeps connection open
2. Remote controller connects to `/control/{id}`
3. Messages from R58 are forwarded to all controllers
4. Messages from controllers are forwarded to R58
5. Relay only forwards messages, doesn't inspect content

## Environment Variables

- `PORT` - Port to listen on (default: 8080)

## Deployment on Coolify

1. Create new service in Coolify
2. Set service name: `r58-relay`
3. Set domain: `relay.r58.itagenten.no`
4. Enable WebSocket support
5. Deploy from this directory

## Local Testing

```bash
npm install
npm start
```

Test with wscat:
```bash
# Terminal 1: R58 unit
wscat -c ws://localhost:8080/unit/test-unit

# Terminal 2: Controller
wscat -c ws://localhost:8080/control/test-unit

# Send messages in either terminal, they should appear in the other
```

## Notes

- Relay is stateless - no message persistence
- If R58 disconnects, controllers receive error messages
- Multiple controllers can connect to same unit
- Only one R58 per unit-id (new connection replaces old)

