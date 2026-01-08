# 🎯 START HERE - R58 Remote Access Guide

**Last Updated**: December 26, 2025  
**Status**: ✅ STABLE & WORKING

---

## 📋 For Chat Agents & Future Reference

This document provides the **essential information** you need to work with the R58 recorder system remotely.

---

## 🚀 Quick Commands

### Connect to R58 via SSH
```bash
./connect-r58-frp.sh
```

### Deploy Code to R58
```bash
./deploy-simple.sh
```

### Check SSH Stability
```bash
./check-frp-status.sh
```

---

## 🌐 Web Access

- **Studio Multiview**: https://app.itagenten.no/static/studio.html
- **Main App**: https://app.itagenten.no/static/app.html
- **Guest Portal**: https://app.itagenten.no/static/guest.html
- **Dev Tools**: https://app.itagenten.no/static/dev.html
- **API Status**: https://app.itagenten.no/status

---

## 🔑 Key Information

### SSH Access
- **Method**: FRP Tunnel (NOT Cloudflare)
- **VPS**: 65.109.32.111
- **Port**: 10022
- **User**: linaro
- **Auth**: SSH key (credentials managed separately)
- **Stability**: ✅ 100% tested

### R58 Device
- **Local Path**: `/opt/preke-r58-recorder`
- **Service**: `preke-recorder.service`
- **Restart**: `sudo systemctl restart preke-recorder`
- **Logs**: `sudo journalctl -u preke-recorder -n 50`

### Git Repository
- **Branch**: feature/remote-access-v2
- **Remote**: https://github.com/mBelstad/preke-r58-recorder

---

## 📚 Documentation Structure

1. **START_HERE.md** ← You are here
2. **[REMOTE_ACCESS.md](REMOTE_ACCESS.md)** - Complete remote access guide
3. **[DEPLOYMENT_SUCCESS_DEC26.md](DEPLOYMENT_SUCCESS_DEC26.md)** - Latest deployment status
4. **[TESTING_SUMMARY.md](TESTING_SUMMARY.md)** - Browser testing results
5. **[CLEANUP_COMPLETE.md](CLEANUP_COMPLETE.md)** - Cleanup summary

### Historical Docs
- Archived in `docs/archive-dec26/` - Don't use these, they reference obsolete methods

---

## ⚠️ Important Notes

### ✅ DO Use
- `connect-r58-frp.sh` - FRP tunnel SSH
- `deploy-simple.sh` - Primary deployment
- FRP tunnel on port 10022
- REMOTE_ACCESS.md documentation

### ❌ DON'T Use
- ~~Cloudflare Tunnel~~ (removed)
- ~~r58.itagenten.no hostname~~ (doesn't exist)
- ~~Any scripts with "cloudflared"~~ (deleted)
- ~~Archived docs~~ (outdated)

---

## 🛠️ Common Tasks

### Deploy New Code
```bash
# 1. Commit and push locally
git add .
git commit -m "Your changes"
git push

# 2. Deploy to R58
./deploy-simple.sh
```

### Check System Status
```bash
./connect-r58-frp.sh "sudo systemctl status preke-recorder"
```

### View Live Logs
```bash
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -f"
```

### Restart Service
```bash
./connect-r58-frp.sh "sudo systemctl restart preke-recorder"
```

---

## 🔧 Troubleshooting

### SSH Not Working?
1. Check port: `nc -zv 65.109.32.111 10022`
2. Run diagnostics: `./check-frp-status.sh`
3. Try local: `./connect-r58-local.sh` (if on same network)
4. See: [FRP_SSH_FIX.md](FRP_SSH_FIX.md)

### Deployment Fails?
1. Test SSH: `./connect-r58-frp.sh "hostname"`
2. Check service: `./connect-r58-frp.sh "sudo systemctl status preke-recorder"`
3. View logs: `./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 50"`

### Web Interface Not Loading?
1. Check if service is running
2. Check API: https://app.itagenten.no/status
3. Check nginx logs on VPS (if you have access)

---

## 🖥️ Desktop App (Preke Studio)

The Electron desktop app (`packages/desktop`) has a test helper for easy testing:

```bash
cd packages/desktop
npm run test:launch    # Start with debugging
npm run test:logs      # View logs
npm run test:build     # Rebuild & restart
npm run test:stop      # Stop app
```

**Browser tools:** After `test:launch`, use `http://localhost:9222` with Cursor's browser tools.

**Full docs:** See `packages/desktop/TESTING.md`

---

## 📦 Available Scripts

### Core Scripts (Use These)
- `connect-r58-frp.sh` - SSH to R58 (PRIMARY)
- `deploy-simple.sh` - Deploy code (PRIMARY)
- `connect-r58-local.sh` - SSH on local network (backup)
- `deploy.sh` - Alternative deployment
- `ssh-setup.sh` - Setup SSH keys
- `check-frp-status.sh` - FRP diagnostics

### Do Not Use (Deleted)
- ~~connect-r58.sh~~ (Cloudflare)
- ~~deploy_*.sh~~ (Various old scripts)
- ~~test_and_deploy_*.sh~~ (Old tests)

---

## 💡 For Chat Agents

When helping with this project:
1. **Always use FRP tunnel** for remote access (port 10022)
2. **Never reference Cloudflare** - we don't use it anymore
3. **SSH is stable** - tested 100% working
4. **Primary script is** `connect-r58-frp.sh`
5. **Deployment script is** `deploy-simple.sh`
6. **Documentation starts with** REMOTE_ACCESS.md
7. **R58 path is** `/opt/preke-r58-recorder` (not /home/linaro/)
8. **Git branch is** `feature/remote-access-v2`
9. **Desktop app testing**: Use `npm run test:launch` in `packages/desktop`
10. **Desktop app logs**: `npm run test:logs` or `~/Library/Logs/preke-studio/main.log`

---

## ✅ System Status (As of Dec 26, 2025)

- SSH via FRP: ✅ STABLE (100% success rate)
- Deployment: ✅ WORKING
- Web Interface: ✅ OPERATIONAL  
- Camera Streams: ✅ LIVE (CAM 3 & 4 confirmed)
- WebRTC/WHEP: ✅ IMPLEMENTED
- Documentation: ✅ COMPLETE

---

## 🎯 Next Steps

1. Read [REMOTE_ACCESS.md](REMOTE_ACCESS.md) for complete guide
2. Test SSH: `./connect-r58-frp.sh "hostname"`
3. Deploy if needed: `./deploy-simple.sh`
4. Access web: https://app.itagenten.no/static/studio.html

---

**Everything works! This is a stable, production-ready system.** 🚀

For detailed information, see [REMOTE_ACCESS.md](REMOTE_ACCESS.md)
