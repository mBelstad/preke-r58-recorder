# Coolify Manual Deployment Guide for R58 Services

## Status

✅ Manual containers removed  
⏳ Ready for Coolify dashboard deployment

## Overview

This guide walks through deploying R58 TURN API and Relay services using Coolify's native dashboard. This ensures proper Traefik integration, automatic SSL certificates, and managed deployments.

---

## Prerequisites

- [x] Manual Docker containers removed
- [ ] Access to Coolify dashboard (`http://65.109.32.111:8000`)
- [ ] GitHub repository accessible: `mBelstad/preke-r58-recorder`
- [ ] Branch: `feature/remote-access-v2`
- [ ] DNS records configured:
  - `api.r58.itagenten.no` → `65.109.32.111`
  - `relay.r58.itagenten.no` → `65.109.32.111`

---

## Part 1: Create Project

### Step 1: Access Coolify Dashboard

1. Open browser: `http://65.109.32.111:8000`
2. Log in with your credentials

### Step 2: Create New Project

1. Click **"Projects"** in sidebar
2. Click **"+ New Project"**
3. Fill in details:
   - **Name**: `r58-infrastructure`
   - **Description**: `R58 remote access infrastructure services`
4. Click **"Create"**

### Step 3: Create Environment

1. Inside the project, click **"+ New Environment"**
2. Fill in:
   - **Name**: `production`
3. Click **"Create"**

---

## Part 2: Deploy TURN API Service

### Step 1: Add New Resource

1. Navigate to `r58-infrastructure` → `production`
2. Click **"+ New Resource"**
3. Select **"Application"**

### Step 2: Configure Source

1. **Source Type**: Select **"Git Repository"**
2. **Git Provider**: Select your GitHub connection (or add new)
3. **Repository**: `mBelstad/preke-r58-recorder`
4. **Branch**: `feature/remote-access-v2`
5. **Build Pack**: Select **"Dockerfile"**
6. **Dockerfile Location**: `coolify/r58-turn-api/Dockerfile`
7. **Docker Build Context**: `coolify/r58-turn-api`

### Step 3: Configure Application

1. **Name**: `r58-turn-api`
2. **Port**: `3000`
3. **Domains**: `api.r58.itagenten.no`

### Step 4: Add Environment Variables

Click **"Environment Variables"** tab and add:

| Key | Value | Is Secret |
|-----|-------|-----------|
| `CF_TURN_ID` | `79d61c83455a63d11a18c17bedb53d3f` | No |
| `CF_TURN_TOKEN` | `9054653545421be55e42219295b74b1036d261e1c0259c2cf410fb9d8a372984` | Yes |
| `PORT` | `3000` | No |

### Step 5: Deploy

1. Click **"Deploy"** button
2. Wait for build to complete (check logs)
3. Verify deployment status shows "Running"

### Step 6: Verify

```bash
curl https://api.r58.itagenten.no/health
# Expected: {"status":"ok","service":"r58-turn-api"}

curl https://api.r58.itagenten.no/turn-credentials
# Expected: JSON with iceServers array
```

---

## Part 3: Deploy Relay Service

### Step 1: Add New Resource

1. In the same environment, click **"+ New Resource"**
2. Select **"Application"**

### Step 2: Configure Source

1. **Source Type**: **"Git Repository"**
2. **Git Provider**: Same as TURN API
3. **Repository**: `mBelstad/preke-r58-recorder`
4. **Branch**: `feature/remote-access-v2`
5. **Build Pack**: **"Dockerfile"**
6. **Dockerfile Location**: `coolify/r58-relay/Dockerfile`
7. **Docker Build Context**: `coolify/r58-relay`

### Step 3: Configure Application

1. **Name**: `r58-relay`
2. **Port**: `8080`
3. **Domains**: `relay.r58.itagenten.no`

### Step 4: Add Environment Variables

| Key | Value |
|-----|-------|
| `PORT` | `8080` |

### Step 5: Deploy

1. Click **"Deploy"** button
2. Wait for build to complete
3. Verify deployment status shows "Running"

### Step 6: Verify

```bash
curl https://relay.r58.itagenten.no/health
# Expected: {"status":"ok","service":"r58-relay","units":0,"controllers":0}
```

---

## Part 4: SSL Certificates

Coolify with Traefik will automatically:
1. Request Let's Encrypt certificates for both domains
2. Configure HTTPS redirects
3. Renew certificates before expiration

**Note**: Certificate issuance takes 1-2 minutes after first deployment.

---

## Troubleshooting

### Build Fails

**Check**:
1. Build logs in Coolify dashboard
2. Dockerfile syntax in repository
3. GitHub repository access

**Fix**:
- Verify branch name is correct
- Check Dockerfile paths
- Ensure GitHub connection is active

### Domain Not Accessible

**Check**:
1. DNS propagation: `dig api.r58.itagenten.no`
2. Container status in Coolify
3. Traefik logs

**Fix**:
- Wait for DNS (5-10 minutes)
- Verify domain spelling
- Check Traefik routing rules

### SSL Certificate Not Issued

**Check**:
1. Domain resolves to correct IP
2. Ports 80/443 open
3. Let's Encrypt rate limits

**Fix**:
- Verify DNS is correct
- Check firewall rules
- Wait and retry if rate limited

### Service Returns 503

**Check**:
1. Container logs in Coolify
2. Application port configuration
3. Health check settings

**Fix**:
- Verify PORT environment variable
- Check application starts correctly
- Review container logs for errors

---

## Post-Deployment

### Update R58 Publishers

Once services are verified working, update R58 camera publishers:

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./connect-r58.sh "mkdir -p /opt/preke-r58-recorder/scripts"
scp scripts/update-publishers-with-turn.sh linaro@r58.itagenten.no:/tmp/
./connect-r58.sh "sudo bash /tmp/update-publishers-with-turn.sh"
./connect-r58.sh "sudo systemctl restart ninja-publish-cam{1..4}"
```

### Monitor Services

In Coolify dashboard:
- View real-time logs
- Monitor resource usage
- Check deployment history
- Manage environment variables

---

## Advantages of Coolify Deployment

✅ **Automatic SSL** - Let's Encrypt certificates managed automatically  
✅ **Easy Updates** - Redeploy with one click  
✅ **Centralized Logs** - All logs in one place  
✅ **Environment Management** - Easy to update env vars  
✅ **Rollback Support** - Revert to previous deployments  
✅ **Health Monitoring** - Built-in health checks  
✅ **Zero Downtime** - Rolling updates supported

---

## Next Steps

1. ✅ Deploy services via Coolify dashboard (follow this guide)
2. ⏳ Verify services accessible via HTTPS
3. ⏳ Update R58 publishers to use new TURN API
4. ⏳ Test remote access
5. ⏳ Proceed with Fleet Management implementation

---

## Support

- **Coolify Docs**: https://coolify.io/docs
- **Coolify Discord**: https://coollabs.io/discord
- **R58 Issues**: GitHub repository issues

---

**Created**: December 21, 2025  
**Status**: Ready for deployment  
**Manual containers**: Removed ✅

