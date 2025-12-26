# Cleanup Plan - Remove Obsolete Scripts & Docs

## ✅ Scripts to KEEP (Working with FRP)

### Connection Scripts:
- **connect-r58-frp.sh** - PRIMARY, FRP tunnel, 100% stable ✅
- **connect-r58-local.sh** - Backup, local network access ✅

### Deployment Scripts:
- **deploy-simple.sh** - PRIMARY, simple FRP deployment ✅
- **deploy.sh** - Alternative FRP deployment ✅
- **ssh-setup.sh** - FRP SSH key setup ✅
- **check-frp-status.sh** - FRP diagnostics ✅

### Deployment Folder (VPS-side):
- **deployment/deploy-coolify.sh** - VPS deployment ✅
- **deployment/r58-whip-publisher.sh** - R58 streaming ✅
- **deployment/mediamtx-coolify.yml** - MediaMTX config ✅
- **deployment/docker-compose-coolify.yml** - Docker compose ✅
- **deployment/nginx.conf** - Nginx config ✅
- **deployment/README.md** - Deployment docs ✅

### Coolify Folder (VPS management):
- **coolify/** - Keep all (VPS-side, might be useful)

---

## ❌ Scripts to DELETE (Obsolete/Cloudflare)

### Connection Scripts:
- ❌ **connect-r58.sh** - Uses Cloudflare Tunnel (obsolete)

### Deployment Scripts:
- ❌ **deploy_to_r58.sh** - Old R58 deployment
- ❌ **deploy_now.sh** - Uses r58.itagenten.no hostname
- ❌ **deploy_remote_mixer.sh** - Uses cloudflared
- ❌ **deploy_hybrid_mode.sh** - Uses r58.itagenten.no
- ❌ **deploy_cairo.sh** - Uses r58.itagenten.no
- ❌ **deploy_plugin_refactor.sh** - Old plugin deploy
- ❌ **deploy_headless.sh** - References Cloudflare
- ❌ **test_and_deploy_mixer.sh** - Old test script
- ❌ **test_reveal_deployment.sh** - Old test script
- ❌ **update_r58_software.sh** - If obsolete

### Test/Development Scripts (Review):
- ❌ **test-zerotier-gateway.sh** - If not using ZeroTier
- ❌ **test-gateway-solution.sh** - If obsolete
- ❌ **add-zerotier-route.sh** - If not using ZeroTier
- ❌ **find-r58.sh** - Not needed with FRP

---

## 📚 Documentation to KEEP

### Current/Working Docs:
- ✅ **FRP_SSH_FIX.md** - FRP troubleshooting
- ✅ **TESTING_SUMMARY.md** - Browser testing
- ✅ **SESSION_SUMMARY_DEC26.md** - Session overview
- ✅ **DEPLOYMENT_SUCCESS_DEC26.md** - Deployment success
- ✅ **UX_REDESIGN_COMPLETE.md** - UX completion
- ✅ **MANUAL_DEPLOYMENT_REQUIRED.md** - Manual steps
- ✅ **deployment/README.md** - Deployment guide

### Architecture Docs:
- ✅ **VDO_ITAGENTEN_ARCHITECTURE.md** - System architecture
- ✅ **WHEP_HDMI_MIXER_SUCCESS.md** - WHEP implementation
- ✅ **README.md** - Main readme

---

## ❌ Documentation to DELETE/ARCHIVE

### Obsolete Implementation Docs (Move to docs/archive/):
- ❌ **DEPLOY_REMOTE_ACCESS.md** - If mentions Cloudflare
- ❌ **SSH_VIA_FRP_SETUP.md** - Redundant with FRP_SSH_FIX.md
- ❌ **FRP_BOOT_SEQUENCE.md** - If outdated
- ❌ **FRP_VERIFICATION.md** - If redundant
- ❌ **FRP_REMOTE_ACCESS_READY.md** - If redundant
- ❌ **CLOUDFLARE_TO_FRP_MIGRATION.md** - Historical, archive
- ❌ **VDO_NINJA_CLOUDFLARE_SETUP.md** - Uses Cloudflare

### Test/Status Docs (Archive):
- ❌ **ZEROTIER_GATEWAY_SETUP.md** - If not using
- ❌ **WEBRTC_GATEWAY_SOLUTION.md** - If obsolete
- ❌ **GATEWAY_SOLUTION_SUMMARY.md** - If obsolete
- ❌ **VPN_CLEANUP_SUMMARY.md** - Historical
- ❌ **WINDOWS_PC_RECOVERY.md** - If obsolete
- ❌ **FRP_ALTERNATIVES.md** - No longer needed
- ❌ **PUBLIC_ROUTING_FIXED.md** - Historical
- ❌ **FIX_NGINX_NOW.md** - Historical

### Multiple Implementation Complete Docs (Keep newest, archive rest):
- Keep: **UX_REDESIGN_COMPLETE.md**
- Keep: **DEPLOYMENT_SUCCESS_DEC26.md**
- Archive rest of IMPLEMENTATION_COMPLETE*.md files

---

## 🎯 Action Items

1. **Delete obsolete scripts** (10 files)
2. **Move historical docs to docs/archive/** (~20 files)
3. **Create REMOTE_ACCESS.md** - Single source of truth
4. **Update README.md** - Remove Cloudflare references
5. **Test stability** - Verify working scripts

---

## 📝 Single Source of Truth Docs (To Create)

### REMOTE_ACCESS.md (New, consolidates everything):
```markdown
# R58 Remote Access Guide

## Quick Start
- SSH: ./connect-r58-frp.sh
- Deploy: ./deploy-simple.sh
- Access: https://r58-api.itagenten.no

## How It Works
- FRP tunnel on Coolify VPS (65.109.32.111:10022)
- All access via FRP (no Cloudflare)

## Troubleshooting
- Check FRP: ./check-frp-status.sh
- See: FRP_SSH_FIX.md
```

This will replace and consolidate many existing docs.

