# R58 Test Matrix

> **Version:** 1.0.0  
> **Last Updated:** January 5, 2026  
> **Status:** Production Reference

This document defines all test cases for the R58 recording system, organized by priority and category.

---

## Priority Definitions

| Priority | Meaning | Release Gate | Test Frequency |
|----------|---------|--------------|----------------|
| **P0** | Critical Path | Must pass for any release | Every build |
| **P1** | Core Functionality | Must pass for major release | Daily |
| **P2** | Reliability | Should pass | Weekly |
| **P3** | Edge Cases | Nice to have | Before major release |

---

## P0 - Critical Path Tests

These tests verify the absolute minimum functionality. If any P0 test fails, the system is unusable.

### P0.1 Service Health

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P0.1.1 | All core services running | `systemctl status r58-api r58-pipeline mediamtx` | All show "active (running)" | smoke-test.sh |
| P0.1.2 | API responds to health check | `curl /api/v1/health` | Returns `{"status": "healthy"}` | smoke-test.sh, health.spec.ts |
| P0.1.3 | Detailed health shows all healthy | `curl /api/v1/health/detailed` | All services "healthy" | health.spec.ts |
| P0.1.4 | Capabilities endpoint works | `curl /api/v1/capabilities` | Returns device info, inputs | health.spec.ts |

### P0.2 Recording Start/Stop

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P0.2.1 | Start recording via API | `POST /api/v1/recorder/start` | Returns 200, session_id | smoke-test.sh |
| P0.2.2 | Recording status updates | `GET /api/v1/recorder/status` during recording | Shows "recording", duration increases | smoke-test.sh |
| P0.2.3 | Stop recording via API | `POST /api/v1/recorder/stop` | Returns 200, status "stopped" | smoke-test.sh |
| P0.2.4 | Recording file created | Check recordings directory | MP4/MKV file exists with correct name | smoke-test.sh |
| P0.2.5 | Recording file playable | `ffprobe` on file | Valid video/audio streams | Manual |
| P0.2.6 | UI start/stop buttons work | Click Start, wait, Click Stop | Timer shows, recording created | recorder.spec.ts |

### P0.3 Video Preview (WHEP)

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P0.3.1 | MediaMTX has active paths | `curl localhost:9997/v3/paths/list` | Shows camera paths, "ready": true | smoke-test.sh |
| P0.3.2 | WHEP endpoint responds | `curl /cam2/whep` | Returns WebRTC offer | Manual |
| P0.3.3 | Browser shows video | Open studio.html, view preview | Video visible, not black | Manual |

### P0.4 WebSocket Connectivity

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P0.4.1 | WebSocket connects | Open app, check Network tab | WS connection established | health.spec.ts |
| P0.4.2 | Events received | Start recording, check WS | `recording.started` event | Manual |
| P0.4.3 | Reconnect after disconnect | Simulate network drop | Auto-reconnects within 10s | Manual |

---

## P1 - Core Functionality Tests

These tests verify that all major features work correctly.

### P1.1 Multi-Camera Recording

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P1.1.1 | Record 2 cameras simultaneously | Start with cam2, cam3 | Both files created | Manual |
| P1.1.2 | Record 3 cameras simultaneously | Start with cam0, cam2, cam3 | All files created | Manual |
| P1.1.3 | Camera selection persists | Select cameras, reload page | Same cameras selected | Manual |
| P1.1.4 | Signal indicators accurate | Connect/disconnect HDMI | Indicator turns green/gray | recorder.spec.ts |

### P1.2 Mixer (VDO.ninja)

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P1.2.1 | Mixer page loads | Navigate to /mixer | VDO.ninja iframe visible | mixer.spec.ts |
| P1.2.2 | VDO.ninja iframe has video | Wait for initialization | Video visible in iframe | mixer.spec.ts |
| P1.2.3 | Sources panel shows cameras | Check sidebar | HDMI sources listed | mixer.spec.ts |
| P1.2.4 | Scene buttons work | Click Scene 1, Scene 2 | Scene changes visually | mixer.spec.ts |
| P1.2.5 | Keyboard shortcuts work | Press 1, 2, 3, T, A | Scenes switch, transitions apply | mixer.spec.ts |
| P1.2.6 | Audio mute buttons work | Click mute icon | Audio indicator changes | mixer.spec.ts |

### P1.3 Go Live / Streaming

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P1.3.1 | Go Live button works | Click "Go Live" | Changes to "End Session", ON AIR badge | mixer.spec.ts |
| P1.3.2 | Program output activates | Go Live, check output | MediaMTX connected message | mixer.spec.ts |
| P1.3.3 | End Session works | Click "End Session" | Returns to Go Live button | mixer.spec.ts |
| P1.3.4 | G key toggles live | Press G twice | Go Live → End Session → Go Live | mixer.spec.ts |

### P1.4 Admin / Device Status

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P1.4.1 | Admin page loads | Navigate to /admin | Admin interface visible | health.spec.ts |
| P1.4.2 | Device status shows | Check device section | Uptime, ID, version shown | health.spec.ts |
| P1.4.3 | Logs viewer works | Check logs section | Recent logs displayed | health.spec.ts |
| P1.4.4 | Support bundle downloads | Click download bundle | ZIP file downloads | Manual |

### P1.5 PWA / Offline

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P1.5.1 | PWA installable | Check Chrome install prompt | "Install" option available | health.spec.ts |
| P1.5.2 | Valid manifest | Check link rel="manifest" | Manifest loads successfully | health.spec.ts |
| P1.5.3 | No critical console errors | Check browser console | No red errors | health.spec.ts |

---

## P2 - Reliability Tests

These tests verify system stability under various conditions.

### P2.1 HDMI Hot-Plug

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P2.1.1 | Connect camera during idle | Plug HDMI while app running | Signal indicator turns green | Manual |
| P2.1.2 | Disconnect camera during idle | Unplug HDMI | Signal indicator turns gray | Manual |
| P2.1.3 | Disconnect during recording | Unplug HDMI while recording | Recording continues for other cameras | Manual |
| P2.1.4 | Reconnect during recording | Replug HDMI while recording | Recording resumes for that camera | Manual |

### P2.2 Network Resilience

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P2.2.1 | API request during network flap | Disconnect network briefly | Request retries and succeeds | Manual |
| P2.2.2 | WebSocket reconnects | Disable network 5s, re-enable | WS reconnects, state syncs | Manual |
| P2.2.3 | Preview recovers | Disconnect 10s, reconnect | Video preview resumes | Manual |
| P2.2.4 | Recording survives network loss | Lose network during recording | Recording continues (local) | Manual |

### P2.3 Disk Space Handling

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P2.3.1 | Refuse start when disk low | Set disk < 2GB free | 507 error, clear message | smoke-test.sh |
| P2.3.2 | Warning when disk near full | Set disk < 10GB | Warning in health/alerts | Manual |
| P2.3.3 | Emergency stop when critical | Disk fills during recording | Recording stops, alert raised | Manual |

### P2.4 Long-Run Stability (Soak Tests)

| ID | Test Case | Duration | Metrics to Check | Automated |
|----|-----------|----------|------------------|-----------|
| P2.4.1 | 2-hour recording | 2 hours | Memory stable, no leaks | Manual |
| P2.4.2 | 4-hour recording | 4 hours | CPU stable, no thermal throttle | Manual |
| P2.4.3 | 8-hour preview | 8 hours | MediaMTX stable, memory stable | Manual |
| P2.4.4 | 24-hour idle | 24 hours | Services stay running, no crashes | Manual |

**Soak Test Checklist:**
- [ ] Memory usage does not grow continuously
- [ ] CPU usage stays under 80%
- [ ] Temperature stays under 80°C
- [ ] No service restarts in logs
- [ ] Recording files are valid at end

### P2.5 Service Recovery

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P2.5.1 | r58-api restart | `systemctl restart r58-api` | API recovers, state correct | Manual |
| P2.5.2 | r58-pipeline restart | `systemctl restart r58-pipeline` | Pipeline recovers | Manual |
| P2.5.3 | mediamtx restart | `systemctl restart mediamtx` | Streams resume | Manual |
| P2.5.4 | All services restart | Restart all | System fully recovers | Manual |

---

## P3 - Edge Cases

### P3.1 Concurrent Operations

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P3.1.1 | Double-click start | Click Start twice quickly | Only one recording starts (idempotent) | Manual |
| P3.1.2 | Multiple browser tabs | Open 2 tabs, start recording in 1 | Both tabs show recording state | Manual |
| P3.1.3 | API + UI simultaneous | API start while UI starting | No race condition, one recording | Manual |
| P3.1.4 | Rapid start/stop | Start, stop, start, stop quickly | All operations complete correctly | Manual |

### P3.2 Error Handling

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| P3.2.1 | Invalid API request | `POST /recorder/start` with bad JSON | 400 error, helpful message | Manual |
| P3.2.2 | Recording already running | Start when already recording | 409 Conflict | Manual |
| P3.2.3 | Stop when not recording | Stop when idle | 400 or idempotent success | Manual |
| P3.2.4 | Invalid camera ID | Start with "cam99" | Error message about invalid input | Manual |

### P3.3 Browser Compatibility

| ID | Test Case | Browser | Expected Result | Automated |
|----|-----------|---------|-----------------|-----------|
| P3.3.1 | Chrome desktop | Chrome 120+ | Full functionality | Playwright |
| P3.3.2 | Safari desktop | Safari 17+ | Core functionality | Manual |
| P3.3.3 | Firefox desktop | Firefox 120+ | Core functionality | Manual |
| P3.3.4 | Chrome mobile | Android Chrome | Responsive UI, view-only | Playwright (mobile) |
| P3.3.5 | Safari mobile | iOS Safari | Responsive UI, view-only | Manual |

### P3.4 Performance

| ID | Test Case | Metric | Target | Automated |
|----|-----------|--------|--------|-----------|
| P3.4.1 | Page load time | FCP | < 1.5s | health.spec.ts |
| P3.4.2 | DOM ready | DOMContentLoaded | < 3s | health.spec.ts |
| P3.4.3 | API response time | /health | < 50ms | Manual |
| P3.4.4 | Recording start latency | Start to recording | < 1s | Manual |
| P3.4.5 | Memory on navigation | Multiple navigations | No leaks | health.spec.ts |

---

## Cross-Platform Tests

### Electron (macOS)

| ID | Test Case | Steps | Expected Result | Automated |
|----|-----------|-------|-----------------|-----------|
| E.1 | App launches | `npm run test:launch` | App window visible | test-helper.js |
| E.2 | CDP available | Check localhost:9222 | CDP endpoints listed | test-helper.js |
| E.3 | No console errors | Check logs | No critical errors | test-helper.js |
| E.4 | Device discovery | Connect to R58 | R58 appears in list | Manual |
| E.5 | Recording via Electron | Start/stop recording | Works same as browser | Manual |

### Browser Mode Limitations

| Feature | Electron | Browser | Notes |
|---------|----------|---------|-------|
| Device discovery | Yes | No | Requires mDNS/Bonjour |
| Local network direct | Yes | Limited | CORS restrictions |
| Tailscale integration | Yes | No | Native API required |
| Offline support | Full | Partial | PWA limitations |

---

## Failure Tests (Chaos Engineering)

### Controlled Failure Scenarios

| ID | Test Case | How to Trigger | Expected Behavior | Recovery |
|----|-----------|----------------|-------------------|----------|
| F.1 | HDMI disconnected mid-record | Unplug cable | Recording continues, input marked offline | Replug cable |
| F.2 | Network drop (local) | Disable network | Recording continues, UI shows disconnected | Re-enable network |
| F.3 | Disk fills up | Fill disk to < 500MB | Recording stops, alert raised | Free space |
| F.4 | Service killed | `kill -9 r58-api` | systemd restarts, state recovers | Automatic |
| F.5 | Power loss simulation | `sudo reboot -f` | Services start on boot, no corruption | Reboot |

---

## Test Execution Checklist

### Pre-Release Smoke Test (5 minutes)

```bash
# 1. Check services
./connect-r58-frp.sh "sudo systemctl status r58-api r58-pipeline mediamtx"

# 2. Run automated smoke test
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && ./scripts/smoke-test.sh"

# 3. Quick manual check
# Open https://r58-api.itagenten.no/static/studio.html
# - Video preview visible?
# - Start/stop recording works?

# 4. Check alerts
curl https://r58-api.itagenten.no/api/v1/alerts | jq '.critical_count'
```

### Full Release Test (30 minutes)

1. Run all P0 tests
2. Run all P1 tests
3. Run Playwright E2E: `npm run test:e2e`
4. Test Electron app: `npm run test:launch`
5. Manual mixer test (Go Live, scenes)
6. Document any failures

### Regression Test (1 hour)

1. Full release test
2. Run P2 tests (reliability)
3. 30-minute recording test
4. Hot-plug test
5. Network resilience test

---

## Test Results Template

```markdown
## Test Results - [Date]

**Tester:** [Name]
**Version:** [Git commit/tag]
**Environment:** [R58 device ID / Local]

### P0 Critical Path
| Test | Result | Notes |
|------|--------|-------|
| P0.1.1 Services running | PASS/FAIL | |
| P0.2.1 Recording start | PASS/FAIL | |
| ... | | |

### Summary
- **Total:** X tests
- **Passed:** X
- **Failed:** X
- **Blocked:** X

### Issues Found
1. [Issue description] - [Severity] - [Ticket/Fix]

### Sign-off
- [ ] All P0 tests pass
- [ ] All P1 tests pass
- [ ] No critical issues
```

---

## Related Documentation

- [docs/testing/testing-tool.md](testing-tool.md) - How to run tests
- [docs/SMOKE_TEST_CHECKLIST.md](../SMOKE_TEST_CHECKLIST.md) - Manual checklist
- [docs/ops/debug-runbook.md](../ops/debug-runbook.md) - Troubleshooting

