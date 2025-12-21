# R58 TURN API Service

Provides TURN server credentials for R58 devices using Cloudflare's TURN service.

## Environment Variables

- `CF_TURN_ID` - Cloudflare TURN key ID
- `CF_TURN_TOKEN` - Cloudflare TURN API token
- `PORT` - Port to listen on (default: 3000)

## Endpoints

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "ok",
  "service": "r58-turn-api"
}
```

### GET /turn-credentials
Get fresh TURN credentials

**Response:**
```json
{
  "iceServers": [
    {
      "urls": ["stun:stun.cloudflare.com:3478"],
    },
    {
      "urls": ["turns://turn.cloudflare.com:5349"],
      "username": "...",
      "credential": "..."
    }
  ],
  "expiresAt": "2025-12-22T18:00:00.000Z"
}
```

## Deployment on Coolify

1. Create new service in Coolify
2. Set service name: `r58-turn-api`
3. Set domain: `api.r58.itagenten.no`
4. Configure environment variables
5. Deploy from this directory

## Local Testing

```bash
export CF_TURN_ID=your_turn_id
export CF_TURN_TOKEN=your_turn_token
npm install
npm start
```

Then test:
```bash
curl http://localhost:3000/health
curl http://localhost:3000/turn-credentials
```

