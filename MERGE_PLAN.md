# Merge Plan: Unmerged R58 Branches

## Overview
This document outlines the plan to merge critical code from unmerged branches that contain code that was running on the R58 device.

## Branches to Merge

### 1. `feature/remote-access-v2`
- **Status**: 296 commits ahead of main
- **Key Features**:
  - P1 critical hardening (disk check, IPC retry, watchdog)
  - VDO.ninja integration improvements
  - SSH connection reliability improvements
  - Control panel and bridge work
  - Studio Control Panel with VDO.ninja integration
- **Last Deployment**: December 2025
- **Risk**: HIGH - Contains production hardening that may be running on device

### 2. `feature/p1-hardening`
- **Status**: 301 commits ahead of main
- **Key Features**:
  - P1-P4 hardening work:
    - P1: Disk check, IPC retry, watchdog
    - P2: WebSocket state sync and event buffering
    - P3: Observability - structured logging, MediaMTX health, alerts
    - P4: Performance - degradation policy and frontend API retry
  - All tests passing (125 backend + 57 frontend)
- **Last Deployment**: Unknown
- **Risk**: HIGH - Contains critical production hardening

## Merge Strategy

### Option 1: Merge Both Branches (Recommended)
1. **Merge `feature/p1-hardening` first** (it contains the most complete hardening)
2. **Then merge `feature/remote-access-v2`** (may have additional features)
3. **Resolve conflicts** - Both branches likely have overlapping changes
4. **Test thoroughly** before deploying

### Option 2: Cherry-pick Critical Commits
1. Identify critical commits from both branches
2. Cherry-pick only essential changes
3. More controlled but time-consuming

### Option 3: Create New Integration Branch
1. Create `feature/integration-r58-hardening`
2. Merge both branches into it
3. Resolve all conflicts
4. Test and merge to main

## Recommended Approach: Option 1

### Step-by-Step Plan

#### Phase 1: Preparation
1. ✅ Document current state (this file)
2. Create backup branch: `git branch backup-main-$(date +%Y%m%d)`
3. Ensure working directory is clean

#### Phase 2: Merge feature/p1-hardening
```bash
git checkout main
git merge feature/p1-hardening --no-ff -m "Merge feature/p1-hardening: P1-P4 production hardening"
# Resolve conflicts if any
# Run tests
```

#### Phase 3: Merge feature/remote-access-v2
```bash
git merge feature/remote-access-v2 --no-ff -m "Merge feature/remote-access-v2: VDO.ninja integration and control panel"
# Resolve conflicts if any
# Run tests
```

#### Phase 4: Testing
1. Run all tests (125 backend + 57 frontend)
2. Test on local development environment
3. Test on R58 device (staging if available)

#### Phase 5: Deployment
1. Update deployment script to use `main` branch
2. Deploy to R58 device
3. Monitor logs and functionality

## Conflict Resolution Guide

### Expected Conflict Areas
1. **Backend API changes** - May have overlapping improvements
2. **Frontend components** - UI changes may conflict
3. **Configuration files** - Deployment and service configs
4. **Test files** - Many test files added in both branches

### Resolution Strategy
- Prefer changes from `feature/p1-hardening` for hardening features
- Prefer changes from `feature/remote-access-v2` for VDO.ninja integration
- Manual review for overlapping areas
- Keep all test files (they don't conflict, just add coverage)

## Risk Assessment

### High Risk
- **Breaking changes** in production hardening
- **Missing features** if merge is incomplete
- **Service disruption** if deployment fails

### Mitigation
- Test thoroughly before deployment
- Have rollback plan ready
- Deploy during low-usage period
- Monitor closely after deployment

## Timeline Estimate
- **Preparation**: 30 minutes
- **Merge feature/p1-hardening**: 1-2 hours (depending on conflicts)
- **Merge feature/remote-access-v2**: 1-2 hours (depending on conflicts)
- **Testing**: 2-4 hours
- **Deployment**: 30 minutes
- **Total**: 5-9 hours

## Post-Merge Tasks
1. Update deployment documentation
2. Verify all features work on R58 device
3. Update changelog
4. Tag release if stable
5. Clean up old branches (after verification)

## Notes
- The R58 device may currently be running code from `feature/remote-access-v2`
- The deployment script (`deploy-simple.sh`) currently pushes to `feature/remote-access-v2`
- After merge, update deployment script to use `main` branch
- Consider creating a `production` branch for stable releases

