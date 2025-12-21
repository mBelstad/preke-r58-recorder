# Quick Start Guide - R58 Fleet Management

## What's Been Done ✅

1. **R58 TURN API** - Deployed and working at `https://api.r58.itagenten.no`
2. **R58 WebSocket Relay** - Deployed and working at `https://relay.r58.itagenten.no`
3. **Fleet Manager** - Fully implemented and ready to deploy

---

## What You Need to Do 🚀

### Step 1: Push Fleet Manager to GitHub (2 minutes)

```bash
cd /Users/mariusbelstad/R58\ app/r58-fleet-manager

# Create GitHub repo (via GitHub web interface or CLI)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/r58-fleet-manager.git
git push -u origin main
```

### Step 2: Deploy Fleet Manager to Coolify (10 minutes)

**Option A: Docker Compose (Easiest)**

```bash
# SSH to Coolify server
ssh root@65.109.32.111
# Password: PNnPtBmEKpiB23

# Clone and deploy
cd /opt
git clone https://github.com/YOUR_USERNAME/r58-fleet-manager.git
cd r58-fleet-manager
docker-compose up -d

# Verify
curl http://localhost:3001/health
```

**Option B: Via Coolify Dashboard**

1. Open Coolify dashboard
2. Create new application
3. Source: Git repository (r58-fleet-manager)
4. Build Pack: Dockerfile
5. Context: `api/`
6. Ports: `3001`, `3002`
7. Deploy

### Step 3: Install Agent on R58 (5 minutes)

```bash
# From your Mac
cd /Users/mariusbelstad/R58\ app/r58-fleet-manager/agent
scp -r . linaro@r58.itagenten.no:/tmp/agent/

# SSH to R58
ssh linaro@r58.itagenten.no
cd /tmp/agent

# Install (replace with your Fleet API URL if different)
sudo FLEET_API_URL="ws://fleet.itagenten.no:3002" ./install.sh

# Verify
sudo systemctl status r58-fleet-agent
```

### Step 4: Access Dashboard

Open in browser:
```
http://fleet.itagenten.no:3001
```

You should see your R58 device listed as "online"!

---

## Testing Remote Control

1. **Restart Services**:
   - Click "Restart" button in dashboard
   - R58 services will restart
   - Device will reconnect automatically

2. **Update Software**:
   - Click "Update" button
   - Enter branch name (e.g., "main")
   - R58 will git pull and restart

3. **View Logs**:
   - Click "Logs" button
   - See centralized logs from R58

---

## Troubleshooting

### Fleet API Not Accessible

```bash
# Check if running
docker ps | grep fleet

# Check logs
docker logs r58-fleet-api

# Restart
cd /opt/r58-fleet-manager
docker-compose restart
```

### Agent Not Connecting

```bash
# On R58, check agent status
sudo systemctl status r58-fleet-agent

# View logs
sudo journalctl -u r58-fleet-agent -f

# Restart agent
sudo systemctl restart r58-fleet-agent
```

### Device Not Showing in Dashboard

1. Check agent is running on R58
2. Check Fleet API URL is correct
3. Check WebSocket port 3002 is accessible
4. Check browser console for errors

---

## Next Steps After Testing

1. **Configure DNS** (optional):
   - Add `fleet.itagenten.no` A record → `65.109.32.111`
   - Update Fleet API URL in agent

2. **Add More Devices**:
   - Install agent on additional R58 units
   - Each will auto-register with unique ID

3. **Enable SSL for Fleet API** (recommended):
   - Add Traefik labels to docker-compose
   - Similar to R58 TURN API setup

4. **Customize Dashboard**:
   - Edit `dashboard/index.html`
   - Add venue names, custom metrics, etc.

---

## Files You Need

All files are already created:

**R58 Services** (already deployed):
- `coolify/r58-turn-api/` ✅
- `coolify/r58-relay/` ✅

**Fleet Manager** (ready to deploy):
- `r58-fleet-manager/api/` ✅
- `r58-fleet-manager/agent/` ✅
- `r58-fleet-manager/dashboard/` ✅
- `r58-fleet-manager/docker-compose.yml` ✅

**Documentation**:
- `IMPLEMENTATION_COMPLETE_DEC21.md` - Full details
- `r58-fleet-manager/README.md` - Fleet Manager docs
- `r58-fleet-manager/agent/README.md` - Agent docs

---

## Summary

**Time Required**: ~20 minutes total
- Push to GitHub: 2 min
- Deploy Fleet Manager: 10 min
- Install agent on R58: 5 min
- Test: 3 min

**Result**: Full fleet management system operational!

---

**Questions?** Check `IMPLEMENTATION_COMPLETE_DEC21.md` for detailed information.
