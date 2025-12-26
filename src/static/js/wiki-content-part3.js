// R58 Documentation Wiki - Content Database (Part 3)
// Troubleshooting and History & Decisions

// Extend the wikiContent object
Object.assign(wikiContent, {
    // ========================================
    // TROUBLESHOOTING
    // ========================================
    
    'common-issues': {
        title: 'Common Issues & Solutions',
        simple: \`
Here are the most common problems and how to fix them:

**Problem**: Can't connect via SSH  
**Solution**: Check if port 10022 is accessible

**Problem**: Video not showing in browser  
**Solution**: Check if MediaMTX is running

**Problem**: Recording won't start  
**Solution**: Check if camera is connected and detected

Most issues can be fixed by restarting the service!
        `,
        technical: \`
**Diagnostic Approach**:
1. Check service status
2. View logs
3. Test components individually
4. Verify configuration
5. Restart services

**Common Root Causes**:
- Service crashed (check logs)
- Device busy (another process using camera)
- Configuration error (syntax in YAML)
- Network issue (FRP tunnel down)
- Disk full (no space for recordings)

**Quick Diagnostics**:
\`\`\`bash
# All-in-one health check
./connect-r58-frp.sh "
    systemctl status preke-recorder mediamtx frpc &&
    ss -tlnp | grep -E '8000|8889' &&
    df -h | grep mnt
"
\`\`\`
        `,
        content: \`
## Issue: SSH Connection Fails

**Symptoms**:
- "Connection refused"
- "Permission denied"
- Timeout

**Diagnostics**:
\`\`\`bash
# Test port
nc -zv 65.109.32.111 10022

# Check sshpass
which sshpass
\`\`\`

**Solutions**:
1. Install sshpass: \`brew install sshpass\`
2. Check password is "linaro"
3. Verify VPS is accessible
4. Check FRP tunnel on R58 (requires physical access)

## Issue: Web Interface Not Loading

**Symptoms**:
- 404 Not Found
- Connection timeout
- SSL certificate error

**Diagnostics**:
\`\`\`bash
# Test API
curl -I https://r58-api.itagenten.no/health

# Check service
./connect-r58-frp.sh "systemctl status preke-recorder"
\`\`\`

**Solutions**:
1. Check service is running
2. Verify FRP tunnel is up
3. Clear browser cache
4. Try different browser

## Issue: No Video in Browser

**Symptoms**:
- Black screen
- "Connecting..." forever
- WebRTC error in console

**Diagnostics**:
\`\`\`bash
# Check MediaMTX
./connect-r58-frp.sh "systemctl status mediamtx"

# Check streams
./connect-r58-frp.sh "curl http://localhost:9997/v3/paths/list"
\`\`\`

**Solutions**:
1. Restart MediaMTX: \`sudo systemctl restart mediamtx\`
2. Check camera is streaming
3. Verify browser supports WebRTC
4. Check CORS settings

## Issue: Recording Won't Start

**Symptoms**:
- API returns error
- "Device busy" message
- No file created

**Diagnostics**:
\`\`\`bash
# Check camera device
./connect-r58-frp.sh "v4l2-ctl --list-devices"

# Check if device is in use
./connect-r58-frp.sh "sudo lsof /dev/video60"

# Check disk space
./connect-r58-frp.sh "df -h /mnt/sdcard"
\`\`\`

**Solutions**:
1. Stop conflicting process
2. Restart preke-recorder service
3. Check camera is connected
4. Free up disk space

## Issue: High CPU Usage

**Symptoms**:
- System slow
- Dropped frames
- High temperature

**Diagnostics**:
\`\`\`bash
# Check CPU usage
./connect-r58-frp.sh "top -bn1 | head -20"

# Check encoding method
./connect-r58-frp.sh "cat /opt/preke-r58-recorder/config.yml | grep codec"
\`\`\`

**Solutions**:
1. Verify hardware encoding (mpph264enc)
2. Reduce bitrate
3. Lower resolution
4. Reduce number of active cameras

## Issue: Mixer Not Working

**Symptoms**:
- Mixer status shows "NULL"
- Scene won't apply
- No mixer output

**Diagnostics**:
\`\`\`bash
# Check mixer status
curl https://r58-api.itagenten.no/api/mixer/status

# Check logs
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 100 | grep mixer"
\`\`\`

**Solutions**:
1. Enable mixer in config.yml
2. Restart service
3. Check all cameras are available
4. Verify scene file exists

## Issue: Deployment Fails

**Symptoms**:
- Git pull fails
- Service won't restart
- Code not updating

**Diagnostics**:
\`\`\`bash
# Check git status
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && git status"

# Check for conflicts
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && git diff"
\`\`\`

**Solutions**:
1. Resolve git conflicts
2. Force pull: \`git reset --hard origin/main\`
3. Check file permissions
4. Verify service file is correct
        `,
        keyPoints: [
            'Most issues fixed by restarting services',
            'Check logs first: journalctl -u preke-recorder',
            'Verify services running: systemctl status',
            'Test components individually to isolate problem'
        ],
        tags: ['troubleshooting', 'issues', 'problems', 'solutions']
    },
    
    'ssh-problems': {
        title: 'SSH Connection Problems',
        simple: \`
If you can't connect via SSH:

1. **Check the port is open**:
   \`\`\`bash
   nc -zv 65.109.32.111 10022
   \`\`\`

2. **Verify sshpass is installed**:
   \`\`\`bash
   which sshpass
   \`\`\`

3. **Try manual connection**:
   \`\`\`bash
   ssh -p 10022 linaro@65.109.32.111
   \`\`\`
   Password: linaro

If these don't work, the FRP tunnel may be down (requires physical access to R58).
        `,
        technical: \`
**SSH Connection Chain**:
\`\`\`
Your Computer
  → sshpass (password automation)
  → SSH client
  → 65.109.32.111:10022 (VPS)
  → FRP Server
  → FRP Client (R58)
  → sshd (R58 port 22)
\`\`\`

**Failure Points**:
1. sshpass not installed
2. Network to VPS blocked
3. FRP server down
4. FRP client down (on R58)
5. SSH daemon down (on R58)

**Diagnostic Commands**:
\`\`\`bash
# Test each layer
nc -zv 65.109.32.111 10022           # VPS reachable?
ssh -p 10022 linaro@65.109.32.111   # SSH works manually?
./connect-r58-frp.sh "hostname"     # Full chain works?
\`\`\`
        `,
        content: \`
## Error: "Connection refused"

**Cause**: Port 10022 not accessible

**Diagnostics**:
\`\`\`bash
# Test port
nc -zv 65.109.32.111 10022

# Expected: Connection succeeded
# If fails: Port is blocked or FRP server down
\`\`\`

**Solutions**:
1. Check internet connection
2. Try from different network
3. Contact VPS administrator
4. Check FRP server status (requires VPS access)

## Error: "Permission denied"

**Cause**: Authentication failure

**Diagnostics**:
\`\`\`bash
# Try manual SSH
ssh -p 10022 linaro@65.109.32.111
# Enter password: linaro

# If this works, issue is with sshpass
\`\`\`

**Solutions**:
1. Verify password is "linaro"
2. Check sshpass is installed: \`brew install sshpass\`
3. Try with explicit password: \`export R58_PASSWORD=linaro\`
4. Setup SSH keys for passwordless access

## Error: "sshpass: command not found"

**Cause**: sshpass not installed

**Solution**:
\`\`\`bash
# macOS
brew install sshpass

# Linux (Debian/Ubuntu)
sudo apt-get install sshpass

# Linux (RHEL/CentOS)
sudo yum install sshpass
\`\`\`

## Error: "Connection timed out"

**Cause**: Network issue or FRP tunnel down

**Diagnostics**:
\`\`\`bash
# Test basic connectivity
ping 65.109.32.111

# Test port specifically
nc -zv 65.109.32.111 10022 -w 5
\`\`\`

**Solutions**:
1. Check internet connection
2. Try from different network
3. Wait and retry (temporary network issue)
4. Check FRP tunnel status (requires R58 physical access)

## FRP Tunnel Down (Requires Physical Access)

If FRP tunnel is down, you need physical access to R58:

\`\`\`bash
# Connect monitor and keyboard to R58
# Login as linaro / linaro

# Check FRP client service
sudo systemctl status frpc

# Check FRP SSH tunnel
sudo systemctl status frp-ssh-tunnel

# Restart if needed
sudo systemctl restart frpc
sudo systemctl restart frp-ssh-tunnel

# View logs
sudo journalctl -u frpc -n 50
\`\`\`

## Setup SSH Keys (Optional)

For passwordless access:

\`\`\`bash
# Generate key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy to R58
ssh-copy-id -p 10022 linaro@65.109.32.111

# Test
ssh -p 10022 linaro@65.109.32.111
# Should connect without password
\`\`\`

## Alternative: Local Network Access

If FRP is down, use local network:

\`\`\`bash
# Find R58 on local network
./find-r58.sh

# Connect directly
./connect-r58-local.sh 192.168.x.x
\`\`\`
        `,
        keyPoints: [
            'Test port accessibility with nc -zv',
            'Verify sshpass is installed',
            'Try manual SSH to isolate issue',
            'FRP tunnel issues require physical R58 access'
        ],
        tags: ['ssh', 'connection', 'troubleshooting', 'frp']
    },
    
    'video-issues': {
        title: 'Video & Streaming Issues',
        simple: \`
If video isn't showing:

1. **Check MediaMTX is running**:
   \`\`\`bash
   ./connect-r58-frp.sh "systemctl status mediamtx"
   \`\`\`

2. **Verify camera is streaming**:
   \`\`\`bash
   curl https://r58-api.itagenten.no/status
   \`\`\`

3. **Restart MediaMTX**:
   \`\`\`bash
   ./connect-r58-frp.sh "sudo systemctl restart mediamtx"
   \`\`\`

4. **Check browser console** (F12) for WebRTC errors

Usually a service restart fixes video issues!
        `,
        technical: \`
**Video Pipeline**:
\`\`\`
Camera → GStreamer → MediaMTX → FRP → VPS → Browser
\`\`\`

**Failure Points**:
1. Camera not connected
2. GStreamer pipeline failed
3. MediaMTX not receiving stream
4. FRP tunnel issue
5. Browser WebRTC failure
6. CORS misconfiguration

**Diagnostic Flow**:
\`\`\`bash
# 1. Check camera device
v4l2-ctl --list-devices

# 2. Check GStreamer pipeline
journalctl -u preke-recorder -n 50 | grep ERROR

# 3. Check MediaMTX streams
curl http://localhost:9997/v3/paths/list

# 4. Check FRP tunnel
ss -tlnp | grep 18889

# 5. Test WHEP endpoint
curl -I https://r58-mediamtx.itagenten.no/cam1/whep
\`\`\`
        `,
        content: \`
## Issue: Black Screen in Browser

**Symptoms**:
- Video player shows black
- No error message
- Audio may work

**Diagnostics**:
\`\`\`bash
# Check if stream exists
curl https://r58-api.itagenten.no/status

# Check MediaMTX
./connect-r58-frp.sh "curl http://localhost:9997/v3/paths/list | grep cam1"
\`\`\`

**Solutions**:
1. Verify camera is connected
2. Check camera is enabled in config.yml
3. Restart preke-recorder service
4. Check GStreamer logs for errors

## Issue: "Connecting..." Forever

**Symptoms**:
- Video player stuck on "Connecting..."
- WebRTC negotiation fails
- Browser console shows errors

**Diagnostics**:
\`\`\`bash
# Check MediaMTX WebRTC
./connect-r58-frp.sh "ss -tlnp | grep 8889"

# Test WHEP endpoint
curl -X POST https://r58-mediamtx.itagenten.no/cam1/whep \\
  -H "Content-Type: application/sdp"
\`\`\`

**Solutions**:
1. Check browser supports WebRTC
2. Verify CORS headers (check browser console)
3. Restart MediaMTX
4. Try different browser (Chrome recommended)

## Issue: Video Stuttering/Buffering

**Symptoms**:
- Video plays but freezes
- Audio continues
- Periodic buffering

**Diagnostics**:
\`\`\`bash
# Check CPU usage
./connect-r58-frp.sh "top -bn1 | head -10"

# Check network
ping -c 10 65.109.32.111

# Check bitrate
./connect-r58-frp.sh "cat /opt/preke-r58-recorder/config.yml | grep bitrate"
\`\`\`

**Solutions**:
1. Reduce bitrate in config.yml
2. Check network bandwidth
3. Verify hardware encoding is used
4. Close other bandwidth-heavy applications

## Issue: CORS Errors

**Symptoms**:
- Browser console: "CORS policy blocked"
- Video won't load
- API calls fail

**Diagnostics**:
\`\`\`bash
# Check CORS headers
curl -I -X OPTIONS https://r58-mediamtx.itagenten.no/cam1/whep \\
  -H "Origin: https://example.com"

# Should see: Access-Control-Allow-Origin: *
\`\`\`

**Solutions**:
1. Verify nginx CORS configuration
2. Check MediaMTX webrtcAllowOrigins setting
3. Restart nginx proxy (requires VPS access)

## Issue: No Audio

**Symptoms**:
- Video works
- No audio
- Audio level meters show no signal

**Cause**: Current configuration doesn't capture audio

**Solution**:
Audio capture not yet implemented. Video-only for now.

## Issue: Low Quality Video

**Symptoms**:
- Video is pixelated
- Compression artifacts
- Blurry image

**Diagnostics**:
\`\`\`bash
# Check bitrate setting
./connect-r58-frp.sh "cat /opt/preke-r58-recorder/config.yml | grep -A 5 'cam1:'"
\`\`\`

**Solutions**:
1. Increase bitrate in config.yml
2. Verify resolution is 1920x1080
3. Check camera output quality
4. Use H.265 for better compression

## Issue: HLS Stream Not Working

**Symptoms**:
- WebRTC works
- HLS doesn't load
- 404 on .m3u8 file

**Diagnostics**:
\`\`\`bash
# Check HLS endpoint
curl -I https://r58-mediamtx.itagenten.no/cam1/index.m3u8

# Check MediaMTX HLS settings
./connect-r58-frp.sh "cat /opt/preke-r58-recorder/mediamtx.yml | grep -A 5 hls"
\`\`\`

**Solutions**:
1. Verify hlsAlwaysRemux is enabled
2. Check HLS port (8888) is forwarded
3. Wait 2-3 seconds for HLS segments to generate
4. Restart MediaMTX
        `,
        keyPoints: [
            'Most video issues: restart MediaMTX',
            'Check browser console (F12) for WebRTC errors',
            'Verify CORS headers for cross-origin requests',
            'Test with Chrome for best WebRTC support'
        ],
        tags: ['video', 'streaming', 'webrtc', 'mediamtx', 'troubleshooting']
    },
    
    'logs': {
        title: 'Viewing Logs',
        simple: \`
Logs help you understand what's happening inside the R58.

**View recent logs**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 50"
\`\`\`

**Follow logs live**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -f"
\`\`\`

**Search for errors**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep ERROR"
\`\`\`

Logs show you exactly what went wrong!
        `,
        technical: \`
**Log System**: systemd journald

**Services to Monitor**:
- preke-recorder.service (main application)
- mediamtx.service (streaming server)
- frpc.service (FRP client)

**Log Levels**:
- ERROR: Something failed
- WARNING: Potential issue
- INFO: Normal operation
- DEBUG: Detailed information

**Log Locations**:
- System logs: journalctl
- Application logs: stdout/stderr captured by systemd
- FRP logs: /var/log/frpc.log

**Retention**: Logs kept for 7 days by default
        `,
        content: \`
## View Application Logs

**Last 50 lines**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 50"
\`\`\`

**Last 100 lines**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 100"
\`\`\`

**Follow logs (live)**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -f"
# Press Ctrl+C to stop
\`\`\`

**Since specific time**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder --since '2025-12-26 15:00:00'"
\`\`\`

**Last hour**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder --since '1 hour ago'"
\`\`\`

## View MediaMTX Logs

\`\`\`bash
# Recent logs
./connect-r58-frp.sh "sudo journalctl -u mediamtx -n 50"

# Follow live
./connect-r58-frp.sh "sudo journalctl -u mediamtx -f"

# Errors only
./connect-r58-frp.sh "sudo journalctl -u mediamtx | grep -i error"
\`\`\`

## View FRP Logs

\`\`\`bash
# FRP client service
./connect-r58-frp.sh "sudo journalctl -u frpc -n 50"

# FRP log file
./connect-r58-frp.sh "sudo tail -f /var/log/frpc.log"
\`\`\`

## Search Logs

**Find errors**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep ERROR"
\`\`\`

**Find warnings**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep WARNING"
\`\`\`

**Find specific text**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep 'pipeline'"
\`\`\`

**Case-insensitive search**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep -i 'camera'"
\`\`\`

## Export Logs

**Save to file**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 1000" > r58-logs.txt
\`\`\`

**Save all services**:
\`\`\`bash
./connect-r58-frp.sh "
    echo '=== PREKE-RECORDER ===' &&
    sudo journalctl -u preke-recorder -n 100 &&
    echo '=== MEDIAMTX ===' &&
    sudo journalctl -u mediamtx -n 100 &&
    echo '=== FRP ===' &&
    sudo journalctl -u frpc -n 100
" > r58-all-logs.txt
\`\`\`

## Log Analysis

**Count errors**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep -c ERROR"
\`\`\`

**Find most common errors**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep ERROR | sort | uniq -c | sort -rn"
\`\`\`

**Check service restarts**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder | grep 'Started\\|Stopped'"
\`\`\`

## Clear Old Logs

**Clear all logs** (careful!):
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl --vacuum-time=1d"
# Keeps only last 1 day
\`\`\`

**Clear by size**:
\`\`\`bash
./connect-r58-frp.sh "sudo journalctl --vacuum-size=100M"
# Keeps only last 100MB
\`\`\`

## Common Log Patterns

**Successful start**:
\`\`\`
INFO: Starting preke-recorder
INFO: GStreamer initialized
INFO: MediaMTX connection established
INFO: Camera cam1 preview started
\`\`\`

**Camera error**:
\`\`\`
ERROR: Failed to open device /dev/video60
ERROR: Device or resource busy
\`\`\`

**Pipeline error**:
\`\`\`
ERROR: GStreamer pipeline error
ERROR: Could not negotiate format
\`\`\`

**Network error**:
\`\`\`
WARNING: MediaMTX connection lost
WARNING: Retrying connection...
\`\`\`
        `,
        keyPoints: [
            'Use journalctl to view systemd service logs',
            'grep to search for specific errors',
            'Follow logs live with -f flag',
            'Export logs to file for analysis'
        ],
        tags: ['logs', 'journalctl', 'debugging', 'monitoring']
    },
    
    // ========================================
    // HISTORY & DECISIONS
    // ========================================
    
    'why-frp': {
        title: 'Why We Use FRP',
        simple: \`
We tried many ways to access the R58 remotely. FRP (Fast Reverse Proxy) won because:

1. **It works through firewalls** - No need to configure the router
2. **Supports both TCP and UDP** - Needed for WebRTC
3. **Simple setup** - Just one config file
4. **Reliable** - Stable connections, automatic reconnection

Other solutions either didn't work or were too complicated!
        `,
        technical: \`
**Problem**: R58 is behind NAT with no public IP

**Requirements**:
1. Remote SSH access
2. Remote HTTPS access
3. WebRTC streaming (requires UDP)
4. No router configuration
5. Secure and reliable

**Solutions Evaluated**:
- ❌ Port Forwarding: Requires router access
- ❌ Cloudflare Tunnel: No UDP/WebRTC support
- ❌ ngrok: Paid, less control
- ❌ ZeroTier/Tailscale: Requires client installation
- ✅ FRP: Meets all requirements

**Why FRP Works**:
- TCP tunneling for HTTP/SSH
- UDP tunneling for WebRTC media
- MediaMTX TCP WebRTC support (v1.15.5+)
- Self-hosted (full control)
- Open source and free
        `,
        diagram: \`
flowchart TB
    subgraph Problem[The Problem]
        R58[R58 Behind NAT<br/>No Public IP]
        ROUTER[Home Router<br/>Can't Configure]
        ISP[ISP Firewall]
        
        R58 -.->|Blocked| ROUTER
        ROUTER -.->|Blocked| ISP
    end
    
    subgraph Solution[FRP Solution]
        R58B[R58 Device]
        FRPC[FRP Client]
        TUNNEL[Secure Tunnel]
        FRPS[FRP Server<br/>Public VPS]
        INTERNET[Internet Users]
        
        R58B -->|Outbound OK| FRPC
        FRPC -->|TCP+UDP| TUNNEL
        TUNNEL --> FRPS
        FRPS <--> INTERNET
    end
    
    Problem -.->|Solved by| Solution
    
    style Problem fill:#ffcdd2
    style Solution fill:#c8e6c9
`,
        content: \`
## The Challenge

**Situation**:
- R58 is on a home/office network
- Behind NAT (no public IP)
- Router configuration not accessible
- Need remote access for:
  - SSH (development/debugging)
  - HTTPS (web interfaces)
  - WebRTC (video streaming)

## Solutions Tried

### 1. Cloudflare Tunnel ❌

**What we tried**:
\`\`\`bash
cloudflared tunnel create r58
cloudflared tunnel route dns r58 r58.itagenten.no
\`\`\`

**Why it failed**:
- Cloudflare Tunnel only proxies HTTP/HTTPS (TCP)
- WebRTC requires UDP for media streams
- Even with TURN relay, architectural mismatch
- VDO.ninja P2P couldn't work through tunnel

**Lesson**: HTTP tunnels don't support WebRTC

### 2. Cloudflare TURN Server ❌

**What we tried**:
\`\`\`javascript
iceServers: [{
  urls: 'turns:turn.cloudflare.com:5349',
  username: '...',
  credential: '...'
}]
\`\`\`

**Why it failed**:
- TURN relay adds complexity
- Still couldn't fix P2P through tunnel
- High latency
- Bandwidth costs

**Lesson**: TURN doesn't solve tunnel limitations

### 3. ZeroTier VPN ✅ (But Not Used)

**What we tried**:
\`\`\`bash
zerotier-cli join <network-id>
\`\`\`

**Why it works**:
- Creates virtual LAN
- All protocols work (TCP, UDP, etc.)
- Direct connections

**Why we didn't use it**:
- Requires client installation on every device
- More complex for end users
- FRP is simpler for our use case

### 4. FRP ✅ (Winner!)

**What we use**:
\`\`\`toml
# frpc.toml on R58
serverAddr = "127.0.0.1"  # Via SSH tunnel
serverPort = 7000

[[proxies]]
name = "r58-ssh"
type = "tcp"
localPort = 22
remotePort = 10022

[[proxies]]
name = "mediamtx-whep"
type = "tcp"
localPort = 8889
remotePort = 18889

[[proxies]]
name = "webrtc-udp"
type = "udp"
localPort = 8189
remotePort = 18189
\`\`\`

**Why it works**:
- ✅ TCP tunneling for HTTP/SSH
- ✅ UDP tunneling for WebRTC media
- ✅ MediaMTX TCP WebRTC support
- ✅ Self-hosted (full control)
- ✅ Simple configuration
- ✅ Reliable and stable

## Key Insight

**The breakthrough**: MediaMTX v1.15.5+ added webrtcLocalTCPAddress support.

This enables WebRTC to work over TCP, which FRP can tunnel!

**mediamtx.yml setting**:
- webrtcLocalTCPAddress: :8190
- webrtcAdditionalHosts: ["65.109.32.111:18189"]

Combined with FRP's UDP tunneling for the media path, we get full WebRTC support through the tunnel.

## Architecture Comparison

| Method | SSH | HTTPS | WebRTC | Complexity | Cost |
|--------|-----|-------|--------|------------|------|
| Port Forward | ✅ | ✅ | ✅ | High | Free |
| Cloudflare | ✅ | ✅ | ❌ | Medium | Free |
| ZeroTier | ✅ | ✅ | ✅ | Medium | Free |
| FRP | ✅ | ✅ | ✅ | Low | VPS |

## Current Setup (Verified Dec 26, 2025)

**FRP Tunnel**:
- R58 → SSH tunnel → VPS FRP server
- 8 proxies configured (TCP + UDP)
- 100% stable connection
- ~20ms latency added

**Services Exposed**:
- SSH: port 10022
- API: port 18000
- MediaMTX: port 18889
- WebRTC UDP: port 18189

**Public Access**:
- https://r58-api.itagenten.no (API)
- https://r58-mediamtx.itagenten.no (MediaMTX)
- Valid Let's Encrypt SSL certificates

**Result**: Full remote access with WebRTC streaming! ✅
        `,
        keyPoints: [
            'Cloudflare Tunnel doesn\'t support WebRTC/UDP',
            'FRP provides both TCP and UDP tunneling',
            'MediaMTX TCP WebRTC enables streaming through tunnel',
            'Self-hosted solution with full control'
        ],
        tags: ['frp', 'decisions', 'why', 'remote access', 'history']
    },
    
    'cloudflare-history': {
        title: 'Cloudflare: What We Tried',
        simple: \`
We spent a lot of time trying to use Cloudflare services for remote access. Here's what we learned:

**Cloudflare Tunnel**: Great for websites, but doesn't support WebRTC video streaming.

**Cloudflare TURN**: Tried to use their relay servers, but it didn't solve the fundamental problem.

**Cloudflare Calls**: Their video conferencing service was too complex for our needs.

**Lesson**: Sometimes the simple solution (FRP) works better than the fancy one!
        `,
        technical: \`
**Timeline**:
- Dec 18-22, 2025: Extensive Cloudflare experimentation
- Dec 23, 2025: Realized architectural limitations
- Dec 24, 2025: Switched to FRP
- Dec 25, 2025: FRP working perfectly
- Dec 26, 2025: All Cloudflare code removed

**Services Tried**:
1. Cloudflare Tunnel (cloudflared)
2. Cloudflare TURN (WebRTC relay)
3. Cloudflare Calls (SFU)

**Why None Worked**:
- Fundamental: HTTP tunnels can't carry UDP
- WebRTC requires UDP for media (or special TCP support)
- P2P WebRTC needs direct connections
- Relay architectures add complexity and latency

**Files Removed** (Dec 25, 2025):
- src/cloudflare_calls.py
- src/calls_relay.py
- src/static/js/turn-client.js
- Multiple deployment scripts
- Test files and documentation

**Lessons Learned**: Document in CLOUDFLARE_HISTORY.md
        `,
        content: \`
## What We Tried

### Cloudflare Tunnel (cloudflared)

**Setup**:
\`\`\`bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
chmod +x cloudflared-linux-arm64
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared

# Create tunnel
cloudflared tunnel create r58

# Configure
cat > /etc/cloudflared/config.yml <<EOF
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: r58.itagenten.no
    service: http://localhost:8000
  - service: http_status:404
EOF

# Start
cloudflared tunnel run r58
\`\`\`

**What worked**:
- ✅ HTTPS access to web interface
- ✅ API calls
- ✅ Static file serving
- ✅ Automatic SSL certificates

**What didn't work**:
- ❌ WebRTC video streaming
- ❌ VDO.ninja connections
- ❌ MediaMTX WHEP endpoints
- ❌ Any UDP-based protocols

**Why**: Cloudflare Tunnel only proxies HTTP/HTTPS (TCP layer 7). WebRTC media requires UDP or special TCP support.

### Cloudflare TURN Server

**Setup**:
\`\`\`javascript
// WebRTC configuration
const config = {
  iceServers: [
    {
      urls: 'stun:stun.cloudflare.com:3478'
    },
    {
      urls: 'turns:turn.cloudflare.com:5349?transport=tcp',
      username: '<token-id>',
      credential: '<api-token>'
    }
  ]
};
\`\`\`

**What we hoped**:
- TURN relay could force TCP
- TCP could work through tunnel
- WebRTC would connect via relay

**What actually happened**:
- TURN relay worked in isolation
- But couldn't fix P2P through tunnel
- VDO.ninja still couldn't connect
- Added latency without solving problem

**Why**: Even with TURN forcing TCP, the P2P architecture of VDO.ninja requires direct connections that tunnels can't provide.

### Cloudflare Calls (SFU)

**Setup**:
\`\`\`python
# src/cloudflare_calls.py
import requests

class CloudflareCalls:
    def __init__(self, account_id, app_id, api_token):
        self.base_url = f"https://rtc.live.cloudflare.com/v1/apps/{app_id}"
        self.headers = {"Authorization": f"Bearer {api_token}"}
    
    def create_session(self):
        response = requests.post(
            f"{self.base_url}/sessions/new",
            headers=self.headers
        )
        return response.json()
\`\`\`

**Architecture attempted**:
\`\`\`
Guest Browser → Cloudflare Calls SFU → Relay Process → MediaMTX → Mixer
\`\`\`

**What we hoped**:
- Cloudflare handles WebRTC complexity
- SFU relays streams
- We pull from Cloudflare and push to MediaMTX

**What actually happened**:
- Too complex (3-hop architecture)
- Required maintaining relay processes
- API limitations
- Higher latency
- More points of failure

**Why we abandoned it**: Direct WHIP to MediaMTX is simpler and more reliable.

## The Realization

**Key moment** (Dec 23, 2025):

Testing public VDO.ninja (vdo.ninja) also failed from R58. This proved the issue wasn't our self-hosted setup—it was the network architecture.

**Conclusion**: R58's network blocks WebRTC media, regardless of signaling method.

**Solution**: Use protocols designed for tunneling (WHIP/WHEP over HTTP).

## Migration to FRP

**Dec 24, 2025**: Switched to FRP

**What changed**:
1. Removed all Cloudflare services
2. Setup FRP tunnel
3. Configured MediaMTX for TCP WebRTC
4. Updated nginx for CORS
5. Tested and verified

**Result**: Everything worked immediately!

## Code Cleanup

**Dec 25, 2025**: Removed Cloudflare code

**Files deleted**:
- Python modules (cloudflare_calls.py, calls_relay.py)
- JavaScript clients (turn-client.js)
- Deployment scripts (deploy_turn_*.sh)
- Test files (test-turn-*.sh, test_turn_*.html)
- Documentation (moved to archive)

**Lines of code removed**: ~2,000+

**Complexity reduced**: Significantly

## Lessons for Future

**What we learned**:
1. HTTP tunnels don't support WebRTC
2. TURN doesn't solve tunnel limitations
3. Simpler solutions often work better
4. Test assumptions early
5. Don't over-engineer

**What to try next time**:
1. Check protocol requirements first
2. Test with public services (vdo.ninja)
3. Consider simpler solutions (FRP)
4. Prototype quickly
5. Document what doesn't work

**Documentation**: See CLOUDFLARE_HISTORY.md for full details
        `,
        keyPoints: [
            'Spent 4 days trying Cloudflare services',
            'Fundamental issue: HTTP tunnels can\'t carry WebRTC',
            'FRP solved problem in 1 day',
            'Removed 2,000+ lines of Cloudflare code'
        ],
        tags: ['cloudflare', 'history', 'lessons', 'what-didnt-work']
    },
    
    'alternatives': {
        title: 'Alternatives Considered',
        simple: \`
We evaluated many solutions before settling on our current architecture:

**For Remote Access**:
- ❌ Port Forwarding - Requires router access
- ❌ Cloudflare - No WebRTC support
- ❌ ngrok - Paid service
- ✅ FRP - Perfect fit!

**For Video Streaming**:
- ❌ VDO.ninja P2P - Doesn't work through tunnels
- ❌ Janus Gateway - Too complex
- ✅ MediaMTX WHIP/WHEP - Works great!

**For Encoding**:
- ❌ FFmpeg - No hardware encoder access
- ✅ GStreamer - Full hardware support!

Each choice was made after testing alternatives.
        `,
        technical: \`
**Evaluation Criteria**:
1. Hardware acceleration support
2. Works through NAT/firewall
3. Complexity vs. benefit
4. Maintenance burden
5. Community support
6. Cost

**Decision Matrix**:

| Solution | HW Accel | NAT | Complexity | Support | Cost | Chosen |
|----------|----------|-----|------------|---------|------|--------|
| GStreamer | ✅ | N/A | Medium | ✅ | Free | ✅ |
| FFmpeg | ❌ | N/A | Medium | ✅ | Free | ❌ |
| MediaMTX | N/A | ✅ | Low | ✅ | Free | ✅ |
| Janus | N/A | ✅ | High | ✅ | Free | ❌ |
| FRP | N/A | ✅ | Low | ✅ | VPS | ✅ |
| Cloudflare | N/A | ✅ | Medium | ✅ | Free | ❌ |

**Result**: Current stack is optimal for our requirements.
        `,
        content: \`
## Media Processing

### GStreamer ✅ (Chosen)

**Pros**:
- Direct MPP encoder access (mpph264enc, mpph265enc)
- Hardware RGA support
- Flexible pipeline architecture
- Excellent ARM/RK3588 support
- Python bindings (python3-gi)

**Cons**:
- Steeper learning curve
- Pipeline debugging can be tricky
- Documentation sometimes sparse

**Why chosen**: Only option with full RK3588 hardware support.

### FFmpeg ❌ (Not Chosen)

**Pros**:
- Well-documented
- Simpler command-line interface
- Wide adoption

**Cons**:
- No direct MPP encoder access on RK3588
- Would require software encoding
- 4x higher CPU usage

**Why not chosen**: Can't utilize hardware encoders.

## Streaming Server

### MediaMTX ✅ (Chosen)

**Pros**:
- WHIP/WHEP support (HTTP-based WebRTC)
- TCP WebRTC (webrtcLocalTCPAddress setting)
- Multi-protocol (RTSP, RTMP, HLS, SRT, WebRTC)
- Single Go binary
- Low resource usage
- Active development

**Cons**:
- Relatively new (vs. nginx-rtmp)
- Some features still maturing

**Why chosen**: Only server with WHIP/WHEP and TCP WebRTC.

### Janus Gateway ❌ (Not Chosen)

**Pros**:
- Mature WebRTC gateway
- Plugin architecture
- Good documentation

**Cons**:
- Complex setup (multiple components)
- Requires custom plugins for our use case
- Heavier resource usage
- C-based (harder to modify)

**Why not chosen**: Overkill for our needs, too complex.

### nginx-rtmp ❌ (Not Chosen)

**Pros**:
- Battle-tested
- Simple RTMP server
- Low resource usage

**Cons**:
- No WebRTC support
- RTMP only (high latency)
- No WHIP/WHEP

**Why not chosen**: No WebRTC support.

## Remote Access

### FRP ✅ (Chosen)

**Pros**:
- TCP + UDP tunneling
- Self-hosted (full control)
- Simple configuration
- Reliable
- Free (open source)

**Cons**:
- Requires VPS
- Manual setup
- No built-in SSL (use Traefik)

**Why chosen**: Only solution supporting both TCP and UDP tunneling.

### Cloudflare Tunnel ❌ (Not Chosen)

**Pros**:
- Easy setup
- Automatic SSL
- Free
- DDoS protection

**Cons**:
- HTTP/HTTPS only (no UDP)
- No WebRTC support
- Vendor lock-in

**Why not chosen**: Doesn't support WebRTC.

### ZeroTier ✅ (Alternative)

**Pros**:
- Virtual LAN
- All protocols work
- Easy setup
- Free tier

**Cons**:
- Requires client installation
- More complex for end users
- Another service to manage

**Why not chosen**: FRP is simpler for our use case. ZeroTier is a valid alternative if FRP doesn't work.

### ngrok ❌ (Not Chosen)

**Pros**:
- Very easy setup
- Good documentation
- Built-in SSL

**Cons**:
- Paid for production use
- Less control
- Vendor lock-in

**Why not chosen**: Paid service, less control than FRP.

## Video Mixer

### GStreamer Compositor ✅ (Chosen)

**Pros**:
- Native GStreamer element
- Hardware-accelerated
- Flexible layouts
- Dynamic updates

**Cons**:
- Complex pipeline management
- Manual pad property updates

**Why chosen**: Integrates perfectly with our GStreamer pipelines.

### OBS Studio ❌ (Not Chosen)

**Pros**:
- Feature-rich
- GUI
- Plugins

**Cons**:
- Desktop application (not headless)
- Heavy resource usage
- Hard to automate

**Why not chosen**: Not designed for headless operation.

### VDO.ninja Mixer ❌ (Not Chosen)

**Pros**:
- Browser-based
- Easy to use
- Good for remote guests

**Cons**:
- Requires browser running
- P2P doesn't work through tunnels
- Less control over output

**Why not chosen**: P2P architecture incompatible with tunnels.

## Encoding

### Hardware (MPP) ✅ (Chosen)

**Pros**:
- ~10% CPU usage per stream
- Can encode 4x 1080p simultaneously
- Low power consumption
- Low latency

**Cons**:
- Less quality control than software
- Occasional stability issues

**Why chosen**: Essential for 4-camera performance.

### Software (x264) ❌ (Fallback Only)

**Pros**:
- Better quality control
- More reliable
- More options

**Cons**:
- ~40% CPU per stream
- Can only handle 2-3 streams
- Higher power consumption

**Why not chosen**: Can't handle 4 cameras. Used as fallback only.

## Streaming Protocol: RTSP vs RTMP

### RTSP (TCP) ✅ (Chosen)

**Implementation**:
\`\`\`
v4l2src → encode → h264parse config-interval=-1 → 
  rtspclientsink location=rtsp://localhost:8554/cam1 protocols=tcp latency=0
\`\`\`

**Pros**:
- Lower latency (~50ms less than RTMP)
- TCP transport (no packet loss)
- SPS/PPS with every keyframe (config-interval=-1)
- No muxing overhead
- Better for mixer synchronization

**Cons**:
- Slightly more complex setup

**Why chosen**: Latency critical for mixer - RTSP provides lowest latency to MediaMTX.

### RTMP (via flvmux) ❌ (Rejected)

**Implementation** (old code, removed Dec 26, 2025):
\`\`\`
v4l2src → encode → h264parse → flvmux → rtmpsink location=rtmp://localhost:1935/cam1
\`\`\`

**Pros**:
- Widely supported
- Simple setup
- Works with any RTMP server

**Cons**:
- Higher latency (~100ms FLV muxing)
- Only supports H.264 (flvmux limitation)
- Additional muxing/demuxing overhead
- Not optimal for mixer

**Why rejected**: 
- Latency too high for real-time mixing
- RTSP provides better performance
- No benefit over RTSP for our use case
- flvmux limitation to H.264 only

**Code Removed**: build_preview_pipeline() and build_r58_preview_pipeline() functions deleted (not in use).

---

## Summary

Our current stack (GStreamer + MediaMTX + FRP) was chosen after extensive testing of alternatives. Each component was selected because it's the best (or only) option for our specific requirements:

1. **GStreamer**: Only option with RK3588 hardware support
2. **MediaMTX**: Only server with WHIP/WHEP and TCP WebRTC
3. **FRP**: Only tunnel supporting both TCP and UDP
4. **RTSP**: Lowest latency for streaming to MediaMTX

**Result**: Optimal architecture for 4-camera recording and streaming on R58.
        `,
        keyPoints: [
            'Each technology chosen after testing alternatives',
            'GStreamer: only option with hardware encoder access',
            'MediaMTX: only server with WHIP/WHEP support',
            'FRP: only tunnel supporting TCP + UDP'
        ],
        tags: ['alternatives', 'decisions', 'comparison', 'evaluation']
    }
});

