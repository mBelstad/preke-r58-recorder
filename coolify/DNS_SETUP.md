# DNS Setup for R58 Services

## Required DNS Records

Add these records in Cloudflare DNS for `itagenten.no`:

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|--------------|-----|
| A | api.r58 | 65.109.32.111 | DNS only (gray cloud) | Auto |
| A | relay.r58 | 65.109.32.111 | DNS only (gray cloud) | Auto |

**Important**: 
- Use "DNS only" (gray cloud), NOT "Proxied" (orange cloud)
- Traefik on the Coolify server handles SSL certificates
- Proxied mode would interfere with WebSocket connections

## Steps to Configure

### Option 1: Via Cloudflare Dashboard

1. Log into Cloudflare dashboard
2. Select domain: `itagenten.no`
3. Go to DNS → Records
4. Click "Add record"
5. For TURN API:
   - Type: A
   - Name: api.r58
   - IPv4 address: 65.109.32.111
   - Proxy status: DNS only (click orange cloud to turn gray)
   - TTL: Auto
   - Click "Save"
6. For Relay:
   - Type: A
   - Name: relay.r58
   - IPv4 address: 65.109.32.111
   - Proxy status: DNS only (gray cloud)
   - TTL: Auto
   - Click "Save"

### Option 2: Via Cloudflare API

```bash
# Set your Cloudflare credentials
CF_API_TOKEN="your_cloudflare_api_token"
CF_ZONE_ID="your_zone_id_for_itagenten.no"

# Add api.r58 record
curl -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "api.r58",
    "content": "65.109.32.111",
    "ttl": 1,
    "proxied": false
  }'

# Add relay.r58 record
curl -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "relay.r58",
    "content": "65.109.32.111",
    "ttl": 1,
    "proxied": false
  }'
```

## Verify DNS Propagation

```bash
# Check if DNS is resolving
dig api.r58.itagenten.no
dig relay.r58.itagenten.no

# Should return:
# api.r58.itagenten.no.    300    IN    A    65.109.32.111
# relay.r58.itagenten.no.  300    IN    A    65.109.32.111
```

## Test Services

After DNS propagates (1-5 minutes):

```bash
# Test TURN API
curl https://api.r58.itagenten.no/health
# Expected: {"status":"ok","service":"r58-turn-api"}

# Test TURN credentials
curl https://api.r58.itagenten.no/turn-credentials
# Expected: JSON with iceServers array

# Test Relay
curl https://relay.r58.itagenten.no/health
# Expected: {"status":"ok","service":"r58-relay","units":0,"controllers":0}
```

## SSL Certificates

Traefik will automatically request Let's Encrypt certificates when:
1. DNS records are properly configured
2. Domain resolves to the Coolify server
3. Ports 80 and 443 are accessible

Certificate issuance takes 1-2 minutes after DNS propagation.

## Troubleshooting

### DNS not resolving
- Wait 5-10 minutes for propagation
- Check Cloudflare DNS settings
- Verify proxy status is "DNS only" (gray cloud)

### SSL certificate not issued
- Check Traefik logs: `docker logs coolify-proxy`
- Verify ports 80/443 are open
- Ensure domain resolves correctly

### Service not accessible
- Check if containers are running: `docker ps | grep r58`
- Check container logs: `docker logs r58-turn-api`
- Verify Traefik routing: `docker exec coolify-proxy traefik healthcheck`

