# VDO.Ninja Cloudflare Tunnel Configuration

## Current Status

✅ **Cloudflare Tunnel is running** on R58 (PID 2486)

## Adding VDO.Ninja Route

To enable remote access to VDO.Ninja via Cloudflare Tunnel, you need to add a new hostname route in your Cloudflare dashboard.

### Option 1: Via Cloudflare Dashboard (Recommended)

1. Go to: https://one.dash.cloudflare.com/
2. Navigate to: **Zero Trust** → **Networks** → **Tunnels**
3. Find your tunnel (should be named something like "r58-tunnel")
4. Click **Configure**
5. Go to **Public Hostname** tab
6. Click **Add a public hostname**
7. Configure:
   - **Subdomain**: `vdoninja`
   - **Domain**: `itagenten.no`
   - **Type**: `HTTPS`
   - **URL**: `https://localhost:8443`
   - **TLS Verification**: Disable (because we're using self-signed cert)

### Option 2: Via Config File (Advanced)

Edit `/etc/cloudflared/config.yml` on R58:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/<your-tunnel-id>.json

ingress:
  # Existing routes
  - hostname: recorder.itagenten.no
    service: http://localhost:8000
  
  # NEW: VDO.Ninja route
  - hostname: vdoninja.itagenten.no
    service: https://localhost:8443
    originRequest:
      noTLSVerify: true  # Required for self-signed cert
  
  # Catch-all rule (must be last)
  - service: http_status:404
```

Then restart cloudflared:
```bash
sudo systemctl restart cloudflared
```

## Access URLs After Configuration

Once the route is added:

### Remote Access (via Cloudflare)
- **Director/Mixer**: `https://vdoninja.itagenten.no/?director=r58studio`
- **Guest Join**: `https://vdoninja.itagenten.no/?room=r58studio`
- **View cam1**: `https://vdoninja.itagenten.no/?view=r58-cam1`

### Local Access (LAN)
- **Director/Mixer**: `https://192.168.1.25:8443/?director=r58studio`
- **Guest Join**: `https://192.168.1.25:8443/?room=r58studio`
- **View cam1**: `https://192.168.1.25:8443/?view=r58-cam1`

## Important: WebRTC and Cloudflare Tunnel

⚠️ **Cloudflare Tunnel Limitation**: Cloudflare Tunnel proxies HTTP/HTTPS traffic but **does not proxy UDP** traffic, which WebRTC uses for media streams.

### What This Means

1. **Web UI**: ✅ Works perfectly via Cloudflare Tunnel
   - You can access the VDO.Ninja interface
   - Signaling (WebSocket) works through the tunnel
   
2. **Video/Audio Streams**: ⚠️ Requires TURN server
   - WebRTC media (UDP) cannot traverse Cloudflare Tunnel
   - Remote guests need a TURN server to relay media

### Solution: Add TURN Server

For remote guests to work, add a TURN server parameter to your URLs:

```
https://vdoninja.itagenten.no/?director=r58studio&turn=turn:relay.metered.ca:443
```

#### TURN Server Options

1. **Metered TURN** (Recommended - Free tier)
   - Sign up: https://www.metered.ca/
   - Free tier: 50GB/month
   - Add to URL: `&turn=turn:relay.metered.ca:443&username=YOUR_USERNAME&credential=YOUR_PASSWORD`

2. **Twilio TURN**
   - Sign up: https://www.twilio.com/stun-turn
   - Pay-as-you-go pricing
   - Good for production use

3. **Self-hosted Coturn**
   - Requires separate server with public IP
   - Most control, but more setup

### LAN-Only Mode (No TURN Needed)

If you only need local network access, use `&lanonly` parameter:

```
https://192.168.1.25:8443/?director=r58studio&lanonly
```

This blocks all external connections and only allows devices on the same LAN.

## Testing Remote Access

### Step 1: Test Web UI (Should Work)
```
https://vdoninja.itagenten.no/?director=r58studio
```
- ✅ Should load VDO.Ninja interface
- ✅ Should connect to signaling server
- ⚠️ Video streams may not work without TURN

### Step 2: Test with TURN (For Video)
```
https://vdoninja.itagenten.no/?director=r58studio&turn=turn:relay.metered.ca:443
```
- ✅ Should load interface
- ✅ Should relay video through TURN server
- ✅ Remote guests should work

## Verification

After adding the route, verify it works:

```bash
# From your local machine
curl -I https://vdoninja.itagenten.no

# Should return:
# HTTP/2 200
# server: cloudflare
```

## Troubleshooting

### "This site can't be reached"
- Route not added in Cloudflare dashboard yet
- DNS not propagated (wait 5-10 minutes)
- Check cloudflared service: `sudo systemctl status cloudflared`

### "Connection refused" or "502 Bad Gateway"
- VDO.Ninja service not running: `sudo systemctl status vdo-ninja`
- Wrong port in route (should be 8443)
- TLS verification not disabled for self-signed cert

### Web UI loads but no video
- This is expected without TURN server
- Add `&turn=` parameter to URL
- Or use LAN access: `https://192.168.1.25:8443`

## Security Considerations

1. **Self-signed Certificate**: Cloudflare Tunnel handles SSL termination, so remote users won't see certificate warnings
2. **No Authentication**: VDO.Ninja rooms are accessible to anyone with the URL
3. **Room Passwords**: Consider adding `&password=` parameter for production use
4. **TURN Credentials**: Keep TURN server credentials secure

## Summary

- ✅ Cloudflare Tunnel is running
- 📋 Add `vdoninja.itagenten.no` → `https://localhost:8443` route
- ⚠️ TURN server required for remote video/audio
- ✅ LAN access works without TURN
- ✅ Web UI will work via Cloudflare Tunnel
- ⚠️ Media streams need TURN for remote access

---

**Next Steps**:
1. Add Cloudflare Tunnel route (via dashboard or config)
2. Test remote access to web UI
3. Sign up for TURN server (Metered.ca recommended)
4. Add TURN parameter to URLs for remote guests
