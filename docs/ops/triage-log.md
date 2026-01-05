# R58 Triage Log

> **Version:** 1.0.0  
> **Last Updated:** January 5, 2026  
> **Purpose:** Track issues, decisions, and technical debt

This document tracks findings discovered during system exploration, testing, and production hardening. Each finding includes evidence, impact assessment, options, and resolution status.

---

## Active Findings

### Finding 1: Legacy Admin API Service

**ID:** TRIAGE-001  
**Severity:** Low  
**Status:** ✅ Resolved

**Evidence:**
- `r58-admin-api.service` documented as "Legacy" in `docs/R58_SERVICES.md`
- Running on port 8088
- Purpose: "Original admin API from Mekotronics hardware"
- Current preke-recorder (port 8000) supersedes all functionality

**Impact:**
- Unnecessary resource usage (CPU, memory)
- Potential confusion about which API to use
- Extra attack surface (security)
- Port 8088 occupied

**Options:**

| Option | Risk | Effort | Rollback |
|--------|------|--------|----------|
| A) Disable and monitor for 1 week | Low | 5 min | `systemctl start r58-admin-api` |
| B) Remove completely | Medium | 30 min | Restore from backup |
| C) Document and keep | None | 15 min | N/A |

**Question for Marius:**
Is `r58-admin-api` (port 8088) used by any external tools, hardware diagnostics, or Mekotronics utilities? Can we disable it for testing?

**Decision:** Option A - Disable

**Resolution:** (January 5, 2026)
- `r58-admin-api.service` stopped and disabled
- `r58-fleet-agent.service` also stopped and disabled (not needed)
- To rollback: `sudo systemctl enable --now r58-admin-api`

---

### Finding 2: Multiple Service File Locations

**ID:** TRIAGE-002  
**Severity:** Low  
**Status:** ✅ Resolved

**Evidence:**
Previously scattered service files across multiple directories.

**Impact:**
- Confusion about authoritative source
- Risk of deploying wrong version
- Deployment scripts may copy from wrong location

**Options:**

| Option | Risk | Effort | Rollback |
|--------|------|--------|----------|
| A) Consolidate all to `/services/` | Low | 1 hour | Git revert |
| B) Create deployment script that uses `/services/` as source | Low | 30 min | N/A |
| C) Document current structure | None | 15 min | N/A |

**Question for Marius:**
What's the intended deployment flow for service files? Should we consolidate to a single directory?

**Decision:** Option A - Consolidate to `/services/`

**Resolution:** (January 5, 2026)
New structure:
```
/services/
  preke-recorder.service    # Main API service (active)
  mediamtx.service          # Media server (active)
  /archived/                # Old/unused services
    r58-api.service
    r58-pipeline.service
    r58-mediamtx.service
    r58-fleet-agent.service
    r58-camera-bridge.service
    r58-whep-bridge.service
    vdoninja-bridge.service
    preke-kiosk.service
    disable-headset-irq.service
```
- Removed `/systemd/` directory
- Active services now clearly separated from archived

---

### Finding 3: Recordings Path Inconsistency

**ID:** TRIAGE-003  
**Severity:** Medium  
**Status:** ✅ Resolved

**Evidence:**
- `scripts/smoke-test.sh` uses `/opt/r58/recordings/`
- Memory notes say deployment is at `/opt/preke-r58-recorder`
- `docs/OPERATIONS.md` references `/opt/r58/recordings/`
- Backend code uses configurable path

**Impact:**
- Tests may fail if path doesn't exist
- Recordings may go to wrong location
- Confusion during debugging

**Options:**

| Option | Risk | Effort | Rollback |
|--------|------|--------|----------|
| A) Standardize to `/opt/preke-r58-recorder/recordings/` | Low | 1 hour | Update config |
| B) Create symlink `/opt/r58 → /opt/preke-r58-recorder` | Low | 5 min | Remove symlink |
| C) Make all scripts use config variable | Medium | 2 hours | N/A |

**Question for Marius:**
What's the canonical recordings path on production R58? Is there already a symlink?

**Decision:** Canonical path is `/opt/r58/recordings/`

**Resolution:** (January 5, 2026)
- Confirmed `/opt/r58/recordings/` is the canonical path
- Directory exists on R58 (currently empty)
- Smoke test updated to use this path with fallback to root partition
- Old recordings should be deleted when space is limited

---

### Finding 4: Default SSH Credentials in Documentation

**ID:** TRIAGE-004  
**Severity:** Medium  
**Status:** Open - For Awareness

**Evidence:**
- `START_HERE.md` documents: "Password: linaro"
- FRP connection uses key authentication (good)
- Local SSH would accept password authentication

**Impact:**
- Security risk if device on untrusted network
- Default password is well-known

**Options:**

| Option | Risk | Effort | Rollback |
|--------|------|--------|----------|
| A) Change password on device | Low | 5 min | Set new password |
| B) Disable password auth, require keys | Low | 15 min | Re-enable password auth |
| C) Document as known limitation | None | 5 min | N/A |

**Recommendation:** Option B (disable password auth) for production devices

**Decision:** [Pending]

**Resolution:** [Pending]

---

### Finding 5: CORS Wildcard Configuration

**ID:** TRIAGE-005  
**Severity:** Low (for v1)  
**Status:** Documented - Accepted Risk

**Evidence:**
- `docs/CURRENT_ARCHITECTURE.md` states: "MediaMTX: Adds `Access-Control-Allow-Origin: *`"
- Required for WHEP to work from any browser origin

**Impact:**
- Any website could potentially access streams
- Acceptable for local network / trusted VPS setup
- Would need auth layer for public internet

**Options:**

| Option | Risk | Effort | Rollback |
|--------|------|--------|----------|
| A) Keep wildcard CORS (current) | Low for v1 | None | N/A |
| B) Restrict to known origins | Medium (may break clients) | 2 hours | Revert config |
| C) Add authentication layer | None | 4+ hours | Remove auth |

**Decision:** Accept for v1 - Local network is trusted. Document in security notes.

**Resolution:** Documented in `docs/security/security-notes-v1.md`

---

## Resolved Findings

### Finding R1: IPC Timeout Missing

**ID:** TRIAGE-R001  
**Severity:** High  
**Status:** Resolved

**Evidence:**
- `docs/HARDENING.md` shows this was identified and fixed
- IPC client now has timeout and retry with exponential backoff

**Resolution:**
- Implemented in `packages/backend/r58_api/media/pipeline_client.py`
- Connection timeout: 5 seconds
- Read timeout: 10 seconds
- Max retries: 3 with exponential backoff

---

### Finding R2: No Disk Space Pre-Check

**ID:** TRIAGE-R002  
**Severity:** High  
**Status:** Resolved

**Evidence:**
- `docs/HARDENING.md` shows this was identified and fixed
- Now returns 507 when < 2GB free

**Resolution:**
- Implemented in `packages/backend/r58_api/control/sessions/router.py`
- Pre-check before recording start
- Health endpoint also checks (503 if < 1GB)

---

### Finding R3: Recording Stall Detection Missing

**ID:** TRIAGE-R003  
**Severity:** Critical  
**Status:** Resolved

**Evidence:**
- `docs/HARDENING.md` shows watchdog implemented

**Resolution:**
- `RecordingWatchdog` class in `packages/backend/pipeline_manager/watchdog.py`
- Detects stalls after 30 seconds of no progress
- Emergency stop when disk < 0.5GB

---

### Finding R4: No Structured Logging

**ID:** TRIAGE-R004  
**Severity:** Medium  
**Status:** Resolved

**Evidence:**
- `docs/HARDENING.md` shows structured logging implemented

**Resolution:**
- JSON logging with trace IDs
- `packages/backend/r58_api/logging.py`
- Trace middleware in `packages/backend/r58_api/middleware.py`

---

## Technical Debt Backlog

Items to address in future releases:

| ID | Item | Priority | Effort | Status | Notes |
|----|------|----------|--------|--------|-------|
| TD-001 | Add authentication for remote API | P1 | Medium | Pending | Required for public exposure |
| ~~TD-002~~ | ~~Consolidate service file locations~~ | ~~P2~~ | ~~Low~~ | ✅ Done | Completed 2026-01-05 |
| TD-003 | Add health check for FRP tunnel | P2 | Low | Pending | Better remote monitoring |
| TD-004 | Implement TURN server fallback | P3 | High | Pending | For restrictive networks |
| TD-005 | Add recording file integrity check | P2 | Medium | Pending | Verify files after stop |
| TD-006 | Implement log rotation | P3 | Low | Pending | Prevent disk fill from logs |
| TD-007 | Disable SSH password auth | P2 | Low | Pending | Security hardening |
| TD-008 | Rotate FRP token | P2 | Low | Pending | Per-device tokens |

---

## How to Add New Findings

Use this template:

```markdown
### Finding N: [Title]

**ID:** TRIAGE-XXX  
**Severity:** Critical / High / Medium / Low  
**Status:** Open / In Progress / Resolved

**Evidence:**
[What you observed, log excerpts, reproduction steps]

**Impact:**
[What could go wrong, who is affected]

**Options:**

| Option | Risk | Effort | Rollback |
|--------|------|--------|----------|
| A) [Description] | [Risk] | [Time] | [How to undo] |
| B) [Description] | [Risk] | [Time] | [How to undo] |

**Question for Marius:**
[Specific, actionable question]

**Decision:** [Pending / Chosen option]

**Resolution:** [What was done]
```

---

## Related Documentation

- [docs/ops/system-map.md](system-map.md) - System architecture
- [docs/ops/debug-runbook.md](debug-runbook.md) - Troubleshooting
- [docs/HARDENING.md](../HARDENING.md) - Stability improvements
- [docs/KNOWN_ISSUES.md](../KNOWN_ISSUES.md) - Known issues

