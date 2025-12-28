# Latency Optimization Plan

## Problem Statement

1. **HLS Latency**: 2-10 second latency over Cloudflare Tunnel due to HLS segment-based streaming
2. **Scene Change Latency**: 2-5 seconds when mixer rebuilds pipeline for new sources
3. **Preview Latency**: Preview uses same HLS streams, inheriting the latency

## Root Causes

- **HLS Protocol**: Inherently has 2-6 second latency (segment duration × segment count)
- **Cloudflare Tunnel**: Adds 200-500ms RTT for each request
- **GStreamer Pipeline Rebuild**: Mixer tears down and rebuilds pipeline when sources change
- **Remote Access**: WebRTC is disabled for remote access, forcing HLS usage

## Solutions

### Option 1: WebRTC for Local Access (IMPLEMENTED)

**Status**: ✅ Already implemented, disabled for remote access

**Latency**: <500ms for local access

**Pros**: Ultra-low latency, real-time preview

**Cons**: Doesn't work over Cloudflare Tunnel (NAT/firewall issues)

### Option 2: Optimize HLS Settings (PARTIALLY IMPLEMENTED)

**Status**: ⚠️ Partially done, can be improved

**Current Settings**:

- `hlsSegmentDuration: 2s`
- `hlsPartDuration: 200ms`
- `hlsSegmentCount: 12`

**Recommended Changes**:

```yaml
# For remote access, prioritize reliability over latency
hlsSegmentDuration: 3s  # Increase for better buffering
hlsPartDuration: 300ms  # Increase for fewer requests
hlsSegmentCount: 15     # Increase buffer for unreliable connections

# For local access, prioritize latency
# (Could add separate local HLS path with aggressive settings)
```

**Expected Improvement**: More stable streaming, but 3-5 second latency remains

### Option 3: Mixer Pipeline Optimization (RECOMMENDED)

**Status**: ❌ Not implemented

**Goal**: Eliminate pipeline rebuilds for scene changes**Approach**:

1. **Always-on source pads**: Keep all camera sources connected to compositor
2. **Dynamic pad visibility**: Show/hide pads using `alpha` property instead of rebuilding
3. **Pre-allocated pads**: Allocate compositor sink pads for all possible sources on startup

**Implementation**:

```python
# In MixerCore.__init__
def _build_persistent_pipeline(self):
    """Build pipeline with all sources pre-connected."""
    # Create compositor with pads for all cameras
    for cam_id in ['cam0', 'cam1', 'cam2', 'cam3', 'guest1', 'guest2']:
        self._add_source_pad(cam_id)
    
def apply_scene(self, scene_id):
    """Apply scene by adjusting pad properties, not rebuilding."""
    for slot in scene.slots:
        pad = self.source_pads[slot.source]
        pad.set_property('xpos', slot.x_rel * width)
        pad.set_property('ypos', slot.y_rel * height)
        pad.set_property('width', slot.w_rel * width)
        pad.set_property('height', slot.h_rel * height)
        pad.set_property('alpha', slot.alpha)
        pad.set_property('zorder', slot.z)
```

**Expected Improvement**: Scene changes in <100ms instead of 2-5 seconds

### Option 4: WebRTC Tunneling (ADVANCED)

**Status**: ❌ Not implemented

**Goal**: Enable WebRTC over Cloudflare Tunnel**Approach**:

1. Use TURN server for WebRTC relay
2. Configure Cloudflare Tunnel to support WebRTC signaling
3. Implement WebRTC data channel for control

**Complexity**: High

**Expected Improvement**: <500ms latency even for remote access

### Option 5: SRT Streaming (ALTERNATIVE)

**Status**: ❌ Not implemented

**Goal**: Replace HLS with SRT for lower latency**Approach**:

1. Add SRT output to MediaMTX
2. Use SRT.js or WebCodecs for browser playback
3. Configure for low-latency mode

**Expected Improvement**: 500ms-1s latency for remote access

**Cons**: Requires browser support for SRT or custom player

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 hours)

1. ✅ Fix preview workflow (DONE)
2. ⚠️ Optimize HLS settings for remote stability
3. Add loading indicators for scene changes

### Phase 2: Mixer Optimization (4-6 hours)

1. Refactor mixer to use persistent pipeline
2. Implement dynamic pad property updates
3. Pre-allocate all source pads
4. Test scene change latency

### Phase 3: Advanced (8-12 hours)

1. Implement TURN server for WebRTC relay
2. Add SRT streaming option
3. Create hybrid mode (WebRTC local, SRT/HLS remote)

## Testing Plan

### Test 1: Preview Workflow

- ✅ Click scene button → Preview loads, Program unchanged
- ✅ Click TAKE → Program changes to preview scene
- ✅ Double-click scene → Direct cut to program

### Test 2: HLS Stability

- Test with current settings over Cloudflare Tunnel
- Measure buffering frequency and duration
- Test with optimized settings

### Test 3: Mixer Scene Changes

- Measure time from API call to mixer output change
- Test with current implementation (pipeline rebuild)
- Test with optimized implementation (pad updates)

### Test 4: End-to-End Latency

- Measure glass-to-glass latency (camera to browser)
- Test local vs remote access
- Compare HLS vs WebRTC (when available)

## Acceptance Criteria

### Phase 1 (Current)

- ✅ Preview doesn't affect program
- ✅ TAKE button works correctly
- ⚠️ HLS streams stable (some buffering acceptable for remote)

### Phase 2 (Mixer Optimization)

- Scene changes complete in <500ms
- No pipeline rebuilds for scene changes
- All cameras remain streaming during scene changes

### Phase 3 (Advanced)

- WebRTC works over Cloudflare Tunnel OR
- SRT provides <1s latency for remote access
- Hybrid mode auto-selects best protocol

## Notes

- **Current Status**: Phase 1 mostly complete, HLS stability needs tuning
- **Priority**: Focus on Phase 2 (mixer optimization) for biggest latency improvement