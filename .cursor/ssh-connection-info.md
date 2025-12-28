# SSH Connection Information for Cursor AI

This file contains connection details for the R58 device to enable future SSH connections.

## Connection Details

- **Hostname**: `r58.itagenten.no`
- **Username**: `linaro`
- **Password**: `linaro`
- **Method**: Cloudflare Tunnel (ProxyCommand)

## SSH Configuration

The SSH config is located at `~/.ssh/config` and includes:

```
Host r58.itagenten.no
  ProxyCommand /opt/homebrew/bin/cloudflared access ssh --hostname %h
```

## Connection Command

To connect via SSH, use:
```bash
ssh linaro@r58.itagenten.no
```

Or use the helper script:
```bash
./connect-r58.sh
```

## Alternative: Local Network Access

If Cloudflare Tunnel is unavailable:
- **Local IP**: `192.168.1.25`
- **Command**: `sshpass -p 'linaro' ssh -o StrictHostKeyChecking=no linaro@192.168.1.25`

## Verification

Test connection:
```bash
ssh linaro@r58.itagenten.no "hostname && whoami"
```

Expected output:
```
linaro-alip
linaro
```

