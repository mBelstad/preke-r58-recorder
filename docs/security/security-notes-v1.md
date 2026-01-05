# R58 Security Notes v1

> **Version:** 1.0.0  
> **Last Updated:** January 5, 2026  
> **Scope:** Small-scale / local network deployment  
> **Status:** Assessment Complete

This document provides a pragmatic security assessment for the R58 recording system. It focuses on identifying risks and quick wins appropriate for a v1 local/small-scale deployment.

---

## Threat Model

### Deployment Context

The R58 system is designed for:
- **Local network operation** (trusted LAN)
- **Remote access via VPS** (FRP tunnel through trusted VPS)
- **Small-scale deployment** (1-10 devices)
- **Non-public content** (internal production use)

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                     TRUSTED ZONE                            │
│                                                             │
│  ┌─────────────┐         ┌─────────────┐                   │
│  │ R58 Device  │◄───────►│ Local       │                   │
│  │             │         │ Clients     │                   │
│  └──────┬──────┘         └─────────────┘                   │
│         │                                                   │
│         │ FRP Tunnel (authenticated)                       │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │ VPS         │ ◄── Trusted intermediary                  │
│  │ (Coolify)   │                                           │
│  └──────┬──────┘                                           │
│         │                                                   │
└─────────┼───────────────────────────────────────────────────┘
          │
          │ HTTPS (SSL/TLS)
          ▼
┌─────────────────────────────────────────────────────────────┐
│                   UNTRUSTED ZONE                            │
│                                                             │
│  ┌─────────────┐         ┌─────────────┐                   │
│  │ Remote      │         │ Internet    │                   │
│  │ Clients     │         │ (Public)    │                   │
│  └─────────────┘         └─────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Threat Actors (v1 Scope)

| Actor | Capability | Likelihood | Impact |
|-------|------------|------------|--------|
| Script kiddie on internet | Port scanning, known exploits | Medium | Low |
| Malicious insider on LAN | Full network access | Low | High |
| Compromised VPS | Access to tunnel | Low | Critical |
| Curious employee | Access to UI | Medium | Low |

---

## Exposed Services

### R58 Device

| Port | Service | Protocol | Authentication | Exposure |
|------|---------|----------|----------------|----------|
| 22 | SSH | TCP | Password/Key | LAN + FRP |
| 8000 | r58-api | HTTP | None | LAN + FRP |
| 8080 | vdo-webapp | HTTP | None | LAN |
| 8088 | r58-admin-api | HTTP | None | LAN |
| 8443 | vdo-signaling | HTTPS | None | LAN + FRP |
| 8554 | mediamtx RTSP | TCP | None | LAN |
| 8889 | mediamtx WHEP | HTTP | None | LAN + FRP |
| 9997 | mediamtx API | HTTP | None | LAN |

### VPS (65.109.32.111)

| Port | Service | Protocol | Authentication | Exposure |
|------|---------|----------|----------------|----------|
| 22 | SSH | TCP | Key only | Internet |
| 443 | Traefik | HTTPS | None (SSL only) | Internet |
| 7000 | FRP Server | TCP | Token | Internet |
| 10022 | FRP SSH Tunnel | TCP | Tunneled to R58 | Internet |

### Public Domains

| Domain | Service | SSL | Authentication |
|--------|---------|-----|----------------|
| r58-api.itagenten.no | R58 API | Yes (Let's Encrypt) | None |
| r58-mediamtx.itagenten.no | WHEP Streams | Yes | None |
| r58-vdo.itagenten.no | VDO.ninja | Yes | None |

---

## Risk Assessment

### High Risk

| Risk | Description | Current Mitigation | Recommendation |
|------|-------------|-------------------|----------------|
| **No API Authentication** | Anyone with URL can control recording | VPS access limited | Add basic auth for v2 |
| **SSH Password Auth** | Password authentication enabled | Root password changed from default | Disable password auth completely |
| **CORS Wildcard** | Any website can access streams | Restricted to preke.no/itagenten.no | Add auth for public exposure |

### Medium Risk

| Risk | Description | Current Mitigation | Recommendation |
|------|-------------|-------------------|----------------|
| **Self-signed SSL (VDO.ninja)** | Browser warnings, MitM possible | Local only typically | Use proper certs for production |
| **FRP Token in Config** | Single token for all devices | File permissions | Per-device tokens for fleet |
| **No Rate Limiting** | DoS via API spam | None | Add rate limiting |
| **Recordings Unencrypted** | Stored in plain on disk | Physical security | Encrypt if content is sensitive |

### Low Risk (v1 Acceptable)

| Risk | Description | Why Acceptable |
|------|-------------|----------------|
| Unencrypted local traffic | HTTP on LAN | Trusted network |
| No audit logging | Who did what | Small team, low compliance needs |
| No RBAC | Everyone is admin | Single-operator model |

---

## Quick Wins

### 1. Disable SSH Password Authentication

**Effort:** 15 minutes  
**Impact:** High  

```bash
# On R58 device
sudo sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

**Verify:**
```bash
# Should fail with "Permission denied (publickey)"
ssh linaro@192.168.1.24
```

### 2. Add Basic Auth for Remote API (Optional)

**Effort:** 30 minutes  
**Impact:** Medium  

Add nginx basic auth on VPS for r58-api domain:

```nginx
# On VPS nginx config
location / {
    auth_basic "R58 API";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:18000;
}
```

```bash
# Generate password file
sudo htpasswd -c /etc/nginx/.htpasswd r58admin
```

### 3. Rotate FRP Token

**Effort:** 10 minutes  
**Impact:** Medium  

```bash
# Generate new token
NEW_TOKEN=$(openssl rand -hex 32)

# Update VPS frps config
# Update R58 frpc config
# Restart both services
```

### 4. Restrict MediaMTX API to Localhost

**Effort:** 5 minutes  
**Impact:** Low  

```yaml
# mediamtx.yml
api: true
apiAddress: 127.0.0.1:9997  # Instead of 0.0.0.0
```

---

## Security Checklist

### Before Production Deployment

- [ ] SSH password authentication disabled
- [ ] FRP token rotated from default
- [ ] SSL certificates valid (not self-signed for public)
- [ ] Firewall configured (only needed ports open)
- [ ] Recordings directory has appropriate permissions
- [ ] Secrets not in git repository

### Ongoing Operations

- [ ] Review logs weekly for anomalies
- [ ] Update OS packages monthly
- [ ] Rotate FRP token quarterly
- [ ] Review user access as needed

---

## Secrets Management

### Current Secrets

| Secret | Location | Rotation Frequency |
|--------|----------|-------------------|
| SSH private key | `~/.ssh/r58_key` | Yearly |
| FRP token | `/etc/frp/frpc.toml` | Quarterly |
| VPS SSH key | `~/.ssh/coolify_vps_key` | Yearly |
| JWT secret | `/etc/r58/r58.env` | Yearly |

### Best Practices

1. **Never commit secrets to git** - Use `.env` files, add to `.gitignore`
2. **Use environment variables** - Not hardcoded values
3. **Limit file permissions** - `chmod 600` for key files
4. **Separate dev/prod secrets** - Different tokens per environment

---

## Update Strategy

### OS Updates

```bash
# Check for updates (weekly)
sudo apt update

# Apply security updates (monthly)
sudo apt upgrade -y

# Full upgrade (quarterly, with testing)
sudo apt full-upgrade
```

### Application Updates

```bash
# Pull latest code
cd /opt/preke-r58-recorder
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -e packages/backend

# Restart services
sudo systemctl restart r58-api r58-pipeline
```

### Container Updates (VPS)

```bash
# Update containers
./connect-coolify-vps.sh
docker compose pull
docker compose up -d
```

---

## Incident Response

### If Compromise Suspected

1. **Isolate:** Disconnect R58 from network
2. **Preserve:** Don't delete logs or files
3. **Rotate:** Change all passwords and tokens
4. **Investigate:** Review logs, check for unauthorized recordings
5. **Recover:** Reinstall if necessary

### Log Locations for Investigation

| Component | Log Location |
|-----------|--------------|
| R58 API | `journalctl -u r58-api` |
| SSH | `/var/log/auth.log` |
| VPS nginx | `/var/log/nginx/access.log` |
| FRP | `journalctl -u frpc` |

---

## Future Security Improvements

### v2 Roadmap

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| API Authentication | P1 | Medium | JWT or API key auth |
| HTTPS Everywhere | P1 | Medium | TLS for all internal traffic |
| Audit Logging | P2 | Medium | Who did what, when |
| Rate Limiting | P2 | Low | Prevent API abuse |
| Encrypted Recordings | P3 | High | At-rest encryption |

### Not Recommended for v1

- Full RBAC (overkill for single-operator)
- SSO integration (complexity vs. value)
- Network segmentation (requires infrastructure)

---

## Compliance Notes

### GDPR Considerations

If recording contains personal data:
- Document data retention policy
- Enable deletion capability
- Consider consent mechanisms

### Content Security

If content is sensitive:
- Enable at-rest encryption
- Add watermarking
- Implement access controls

---

## Summary

The R58 system is **appropriate for local network and trusted VPS deployment** with current security posture. For public internet exposure or sensitive content, implement the "Quick Wins" and consider v2 authentication features.

**Current Security Level:** Suitable for internal production use  
**Recommended Actions:** Disable SSH password, rotate FRP token  
**Not Suitable For:** Public internet without authentication

---

## Related Documentation

- [docs/ops/triage-log.md](../ops/triage-log.md) - Issue tracking
- [docs/HARDENING.md](../HARDENING.md) - Stability features
- [docs/CURRENT_ARCHITECTURE.md](../CURRENT_ARCHITECTURE.md) - System architecture

