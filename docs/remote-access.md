# Remote Access Guide

This document describes how to connect to the R58 device remotely via SSH and web interface through Cloudflare Tunnel.

## Prerequisites

1. **Cloudflared installed locally** (macOS):
   ```bash
   brew install cloudflared
   ```

2. **SSH config configured** (already set up):
   ```bash
   # Verify your SSH config
   cat ~/.ssh/config | grep r58.itagenten.no
   ```

## SSH Access via Cloudflare Tunnel

### Connection Method

The R58 device is accessible via SSH through Cloudflare Tunnel using the hostname `r58.itagenten.no`.

### SSH Configuration

Your SSH config should include:
```
Host r58.itagenten.no
  ProxyCommand /opt/homebrew/bin/cloudflared access ssh --hostname %h
```

This is automatically configured when you run:
```bash
cloudflared access ssh-config --hostname r58.itagenten.no
```

### Connecting

**Method 1: Direct SSH (with password)**
```bash
ssh linaro@r58.itagenten.no
```

**Method 2: SSH with key-based auth (if keys are set up)**
```bash
ssh linaro@r58.itagenten.no
```

**Method 3: Using cloudflared directly**
```bash
cloudflared access ssh --hostname r58.itagenten.no --user linaro
```

### Connection Details

- **Hostname**: `r58.itagenten.no`
- **Username**: `linaro`
- **Password**: `linaro` (temporary password)
- **Port**: 22 (via Cloudflare Tunnel)
- **Local IP**: `192.168.1.25` (for local network access)

## Web Interface Access

The web interface is accessible at:
- **URL**: `https://recorder.itagenten.no`
- **Local URL**: `http://192.168.1.25:8000`
- **API Docs**: `https://recorder.itagenten.no/docs`

## Cloudflare Tunnel Status

Check tunnel status on the R58:
```bash
ssh linaro@r58.itagenten.no "sudo systemctl status cloudflared"
```

View tunnel logs:
```bash
ssh linaro@r58.itagenten.no "sudo journalctl -u cloudflared -f"
```

## Troubleshooting

### SSH Connection Fails

1. **Check Cloudflared is running on R58**:
   ```bash
   ssh linaro@r58.itagenten.no "sudo systemctl status cloudflared"
   ```

2. **Verify SSH config**:
   ```bash
   cat ~/.ssh/config | grep r58
   ```

3. **Test Cloudflared locally**:
   ```bash
   cloudflared --version
   ```

4. **Check tunnel configuration on R58**:
   ```bash
   ssh linaro@r58.itagenten.no "cat /etc/cloudflared/config.yml"
   ```

### Web Interface Not Accessible

1. **Check FastAPI service**:
   ```bash
   ssh linaro@r58.itagenten.no "sudo systemctl status preke-recorder"
   ```

2. **Verify local access**:
   ```bash
   ssh linaro@r58.itagenten.no "curl http://localhost:8000/health"
   ```

3. **Check Cloudflare dashboard** for tunnel status and routing configuration

## Local Network Access (Alternative)

If Cloudflare Tunnel is unavailable, you can still access via local network:

```bash
# SSH via local IP
sshpass -p 'linaro' ssh -o StrictHostKeyChecking=no linaro@192.168.1.25

# Web interface
open http://192.168.1.25:8000
```

## Security Notes

- The current password (`linaro`) is temporary and should be changed
- Consider setting up SSH key-based authentication for better security
- Cloudflare Tunnel provides encrypted access but ensure your Cloudflare account is secured
- Regularly update cloudflared on both local machine and R58 device

## Files and Configuration

- **SSH Config**: `~/.ssh/config`
- **R58 Cloudflared Config**: `/etc/cloudflared/config.yml`
- **R58 Cloudflared Service**: `/etc/systemd/system/cloudflared.service`
- **R58 SSH Service**: Standard OpenSSH on port 22

