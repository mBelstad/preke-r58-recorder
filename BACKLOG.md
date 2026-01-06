# Preke Studio - Development Backlog

> **Last Updated:** January 5, 2026

## Version 2.1 - Connection & Performance

### High Priority

#### 1. Smart Connection Priority System
**Status:** 📋 Planned  
**Effort:** Medium (4-6 hours)

Implement intelligent connection routing with priority:

| Priority | Method | Expected Latency | When Used |
|----------|--------|------------------|-----------|
| 1 | LAN Direct | 1-5ms | Same network as R58 |
| 2 | Direct P2P | 2-10ms | Known public IP |
| 3 | Tailscale P2P | 2-20ms | After hole punching |
| 4 | Tailscale DERP | 50-200ms | Relay fallback |
| 5 | FRP Tunnel | 100-300ms | Last resort |

**Implementation:**
- Store multiple addresses per device (LAN IP, Tailscale IP, FRP URL)
- Quick probe phase (~500ms) tries all methods in parallel
- Use first responding connection
- Background upgrade if started on slower route

**Why:** Currently app may start on DERP relay (slow) while P2P establishes, causing 30+ second video delays.

---

#### 2. Device Address Caching
**Status:** 📋 Planned  
**Effort:** Low (2 hours)

Cache known-good connection methods per device:
- Remember last working LAN IP
- Remember Tailscale IP
- Expire cache after 24 hours or on connection failure

---

### Medium Priority

#### 3. Tailscale P2P Pre-warming  
**Status:** 📋 Planned  
**Effort:** Low (1 hour)

Before loading video streams:
- Ping Tailscale device to trigger hole punching
- Wait up to 2 seconds for P2P to establish
- Then load video

---

#### 4. Connection Quality Indicator
**Status:** 📋 Planned  
**Effort:** Low (2 hours)

Show in UI:
- Current connection type (LAN/P2P/DERP/FRP)
- Latency indicator
- Connection health status

---

#### 5. Video Loading Optimization
**Status:** 📋 Planned  
**Effort:** Medium (3 hours)

- Don't load video until best connection is found
- Progressive loading (load one camera, then others)
- Retry with better connection if initial load slow

---

## Version 2.2 - Security & Production

### Medium Priority

#### 6. API Authentication
**Status:** 📋 Planned  
**Effort:** High (8+ hours)

Add authentication for remote API access:
- API key or JWT tokens
- Per-device credentials
- Rate limiting

**Why:** Required before exposing API to public internet.

---

#### 7. Disable SSH Password Auth
**Status:** 📋 Planned  
**Effort:** Low (30 min)

On production devices:
- Disable password authentication
- Require SSH key authentication
- Document key management process

---

#### 8. Per-Device FRP Tokens
**Status:** 📋 Planned  
**Effort:** Low (1 hour)

Generate unique FRP tokens for each device instead of shared token.

---

## Completed (v2.0)

These items were completed during production hardening:

| Item | Completed | Notes |
|------|-----------|-------|
| ✅ FRP Health Check | 2026-01-05 | Added to `/api/v1/health/detailed` |
| ✅ TURN Server Documentation | 2026-01-05 | Documented in `WEBRTC_CONNECTIVITY.md` |
| ✅ Recording Integrity Check | 2026-01-05 | `ffprobe` validation after stop |
| ✅ Log Rotation | 2026-01-05 | `logrotate` config in `deployment/` |
| ✅ Service File Consolidation | 2026-01-05 | All in `/services/` |
| ✅ Disable Auto-Select on Startup | 2026-01-05 | Let user choose device |
| ✅ CORS Restrictions | 2026-01-05 | Restricted to known domains |

---

## Technical Debt

Items to address when time permits:

| ID | Item | Priority | Notes |
|----|------|----------|-------|
| TD-001 | Clean up unused code paths | P3 | After connection refactor |
| TD-002 | Consolidate WebRTC connection logic | P2 | Related to connection priority |
| TD-003 | Add E2E tests for connection scenarios | P3 | LAN/P2P/DERP/FRP |
| TD-004 | Document connection troubleshooting | P2 | For operators |

---

## Ideas / Future Consideration

- WebRTC over WebTransport (when browser support matures)
- Multi-device recording sync
- Cloud backup integration
- Mobile app companion

---

## How to Add Items

Use this format:

```markdown
#### N. Feature Name
**Status:** 📋 Planned | 🚧 In Progress | ✅ Done | ❌ Cancelled
**Effort:** Low (1-2h) | Medium (3-6h) | High (8+h)

Description of the feature and why it's needed.

**Implementation notes if any**
```


