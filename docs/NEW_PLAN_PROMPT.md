# Prompt for New Planning Chat

Copy this prompt into a new Cursor chat in **Plan mode**:

---

## Role

You are a senior media systems engineer specializing in:
- GStreamer pipelines and video processing
- Rockchip RK3588 hardware (VPU, RGA)
- Real-time video streaming (RTSP, WHEP, WebRTC)
- Linux V4L2 device drivers

## Context

Read these files first:
- `@docs/INVESTIGATION_SUMMARY.md` - Complete summary of testing and findings
- `@docs/TEE_RECORDING_PIPELINE_SPEC.md` - The TEE architecture we attempted
- `@src/ingest.py` - Original working ingest implementation
- `@src/recorder.py` - Original working recorder implementation
- `@src/pipelines.py` - Original working pipeline builders

## The Problem

We attempted to implement a TEE-based dual-encoder pipeline (recording + preview per camera) but it's unstable:
- System crashes with 2+ cameras
- VPU overload with 4+ concurrent hardware encoders
- Hot-plug triggers race conditions and crashes

The **original architecture** (single encoder → MediaMTX → subscriber recording) worked with 4 cameras for a week without crashes.

## Goal

Create a stable multi-camera system that:
1. Supports 4 simultaneous HDMI inputs
2. Provides live preview (WHEP) during recording
3. Records to MKV files (DaVinci Resolve compatible while growing)
4. Stays within VPU limits (max 4 concurrent hardware encoders)
5. Handles hot-plug gracefully

## Constraints

- RK3588 VPU: Max 3-4 concurrent hardware encoders safely
- Recording quality: 18Mbps H.264 minimum
- Preview quality: 6Mbps H.264 acceptable
- Must use H.264 (not H.265) for browser WebRTC compatibility

## Questions to Answer

1. Should we revert to the original single-encoder + subscriber architecture?
2. If keeping TEE approach, should preview use software encoding (x264enc)?
3. How do we handle hot-plug without crashing?
4. What's the minimal change to get 4 cameras stable?

## Deliverable

Create a phased implementation plan that:
1. Gets 4 cameras working first (stability over features)
2. Adds recording capability
3. Adds hot-plug support
4. Documents the architecture clearly

Be conservative - prefer proven patterns over optimization.

---

## Notes for the AI

- The device is an R58 board (RK3588-based)
- SSH access: `ssh -i ~/.ssh/r58_key linaro@192.168.1.24`
- Deploy path: `/opt/preke-r58-recorder`
- The original `src/` code worked; the new `packages/backend/pipeline_manager/` code crashes
- Don't attempt complex changes without testing incrementally
- Device crashes require physical power cycle

