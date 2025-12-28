# Coolify Deployment Guide for R58 Services

## Prerequisites

- Access to Coolify server: `ssh root@65.109.32.111`
- Cloudflare TURN credentials (CF_TURN_ID and CF_TURN_TOKEN)
- DNS access to itagenten.no domain

## Step 1: Deploy TURN API Service

### 1.1 Create Service in Coolify

1. Log into Coolify dashboard
2. Click "New Service" → "Docker Compose" or "Dockerfile"
3. Configure:
   - **Name**: `r58-turn-api`
   - **Domain**: `api.r58.itagenten.no`
   - **Source**: Git repository or upload files from `coolify/r58-turn-api/`
   - **Port**: 3000

### 1.2 Set Environment Variables

In Coolify service settings, add:
```
CF_TURN_ID=your_cloudflare_turn_key_id
CF_TURN_TOKEN=your_cloudflare_turn_api_token
PORT=3000
```

### 1.3 Deploy

Click "Deploy" and wait for service to start.

### 1.4 Test

```bash
curl https://api.r58.itagenten.no/health
curl https://api.r58.itagenten.no/turn-credentials
```

Expected: JSON response with TURN credentials.

---

## Step 2: Deploy WebSocket Relay Service

### 2.1 Create Service in Coolify

1. Click "New Service" → "Docker Compose" or "Dockerfile"
2. Configure:
   - **Name**: `r58-relay`
   - **Domain**: `relay.r58.itagenten.no`
   - **Source**: Git repository or upload files from `coolify/r58-relay/`
   - **Port**: 8080
   - **Enable WebSocket**: Yes (important!)

### 2.2 Set Environment Variables

```
PORT=8080
```

### 2.3 Deploy

Click "Deploy" and wait for service to start.

### 2.4 Test

```bash
# Health check
curl https://relay.r58.itagenten.no/health

# WebSocket test (requires wscat: npm install -g wscat)
wscat -c wss://relay.r58.itagenten.no/unit/test
```

---

## Step 3: Configure DNS

In Cloudflare DNS for `itagenten.no`, add/verify:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A or CNAME | api.r58 | 65.109.32.111 | Yes (orange cloud) |
| A or CNAME | relay.r58 | 65.109.32.111 | Yes (orange cloud) |

**Note**: If using Cloudflare proxy, ensure WebSocket support is enabled.

---

## Step 4: Verify Deployment

### Check Services are Running

```bash
ssh root@65.109.32.111
docker ps | grep r58
```

Should show both `r58-turn-api` and `r58-relay` containers running.

### Test TURN API

```bash
curl https://api.r58.itagenten.no/turn-credentials | jq
```

Expected output:
```json
{
  "iceServers": [
    {
      "urls": ["stun:stun.cloudflare.com:3478"]
    },
    {
      "urls": ["turns://turn.cloudflare.com:5349"],
      "username": "...",
      "credential": "..."
    }
  ],
  "expiresAt": "2025-12-22T..."
}
```

### Test Relay

```bash
curl https://relay.r58.itagenten.no/health
```

Expected output:
```json
{
  "status": "ok",
  "service": "r58-relay",
  "units": 0,
  "controllers": 0
}
```

---

## Troubleshooting

### Service won't start

1. Check logs in Coolify dashboard
2. Verify environment variables are set
3. Check Docker container logs: `docker logs <container-id>`

### DNS not resolving

1. Wait for DNS propagation (up to 24 hours, usually minutes)
2. Check DNS with: `dig api.r58.itagenten.no`
3. Verify Cloudflare DNS settings

### WebSocket connection fails

1. Ensure WebSocket is enabled in Coolify service settings
2. Check if Cloudflare proxy is interfering
3. Try direct connection to server IP

### TURN API returns error

1. Verify CF_TURN_ID and CF_TURN_TOKEN are correct
2. Check Cloudflare TURN service is active
3. Test Cloudflare API directly

---

## Security Notes

- TURN credentials are temporary (24h TTL)
- Relay doesn't store messages
- All connections use SSL/TLS
- Consider rate limiting for production

---

## Next Steps

After both services are deployed and tested:
1. Update R58 configuration to use new endpoints
2. Test from R58 device
3. Test remote access via relay
4. Remove Cloudflare Tunnel dependency

