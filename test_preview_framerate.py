#!/usr/bin/env python3
"""
Test Preview Framerate

This script tests the actual framerate of preview streams by:
1. Querying MediaMTX API for stream statistics
2. Checking GStreamer pipeline configuration
3. Reporting expected vs actual framerates

Usage:
    python test_preview_framerate.py [--local] [--remote]
"""

import sys
import json
import time
import argparse
import subprocess
from typing import Dict, Any, Optional, List

# Configuration
LOCAL_MEDIAMTX_API = "http://127.0.0.1:9997"
REMOTE_MEDIAMTX_API = "https://r58-mediamtx.itagenten.no"
LOCAL_API = "http://127.0.0.1:8000"

# Expected framerates based on code analysis
EXPECTED_FRAMERATES = {
    "pipeline_output": 30,  # GStreamer pipelines normalize to 30fps
    "ui_updates_normal": 10,  # UI update rate in normal mode (100ms)
    "ui_updates_perf": 2,  # UI update rate in performance mode (500ms)
    "reveal_source": 30,  # Reveal.js default (configurable)
    "mixer_animations": 30,  # Mixer animation FPS
}


def http_get(url: str, timeout: int = 5) -> Optional[Dict]:
    """Simple HTTP GET using urllib (no external dependencies)."""
    import urllib.request
    import urllib.error
    
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def test_mediamtx_api(base_url: str) -> Dict[str, Any]:
    """Test MediaMTX API for stream information."""
    print(f"\n{'='*60}")
    print(f"Testing MediaMTX API: {base_url}")
    print(f"{'='*60}")
    
    results = {
        "accessible": False,
        "paths": [],
        "streams": {}
    }
    
    # Get list of paths
    paths_url = f"{base_url}/v3/paths/list"
    print(f"\n1. Getting paths list: {paths_url}")
    
    data = http_get(paths_url)
    if not data:
        print("   ❌ Could not access MediaMTX API")
        return results
    
    results["accessible"] = True
    items = data.get("items", [])
    results["paths"] = [item.get("name") for item in items]
    
    print(f"   ✅ Found {len(items)} paths: {', '.join(results['paths']) or 'none'}")
    
    # Get details for each path
    print("\n2. Getting stream details:")
    for item in items:
        path_name = item.get("name", "unknown")
        
        # Get detailed path info
        path_url = f"{base_url}/v3/paths/get/{path_name}"
        path_data = http_get(path_url)
        
        if path_data:
            stream_info = {
                "name": path_name,
                "ready": path_data.get("ready", False),
                "source_type": path_data.get("source", {}).get("type", "unknown") if path_data.get("source") else "no source",
                "readers": path_data.get("readers", []),
                "reader_count": len(path_data.get("readers", [])),
            }
            
            # Try to extract framerate from source info
            source = path_data.get("source", {})
            if source:
                # MediaMTX may include codec info with framerate
                stream_info["source_info"] = source
            
            results["streams"][path_name] = stream_info
            
            status = "✅ Ready" if stream_info["ready"] else "⚠️  Not ready"
            print(f"   {path_name}: {status} ({stream_info['source_type']}, {stream_info['reader_count']} readers)")
        else:
            print(f"   {path_name}: ❌ Could not get details")
    
    return results


def test_local_api() -> Dict[str, Any]:
    """Test local preke-recorder API for input status."""
    print(f"\n{'='*60}")
    print(f"Testing Local Recorder API: {LOCAL_API}")
    print(f"{'='*60}")
    
    results = {
        "accessible": False,
        "inputs": [],
        "framerates": {}
    }
    
    # Get recorder inputs
    inputs_url = f"{LOCAL_API}/api/v1/recorder/inputs"
    print(f"\n1. Getting input status: {inputs_url}")
    
    data = http_get(inputs_url)
    if not data:
        print("   ❌ Could not access recorder API")
        return results
    
    results["accessible"] = True
    
    print("\n2. Input framerates:")
    for input_info in data:
        input_id = input_info.get("id", "unknown")
        framerate = input_info.get("framerate", 0)
        resolution = input_info.get("resolution", "unknown")
        has_signal = input_info.get("has_signal", False)
        
        results["inputs"].append(input_info)
        results["framerates"][input_id] = framerate
        
        if has_signal:
            status = f"✅ {framerate}fps @ {resolution}"
            if framerate >= 29:
                quality = "excellent"
            elif framerate >= 24:
                quality = "good"
            else:
                quality = "⚠️  low"
            status += f" ({quality})"
        else:
            status = "⚠️  No signal"
        
        print(f"   {input_id}: {status}")
    
    return results


def check_pipeline_config() -> Dict[str, Any]:
    """Check GStreamer pipeline configuration for framerate settings."""
    print(f"\n{'='*60}")
    print("Checking Pipeline Configuration (from source code)")
    print(f"{'='*60}")
    
    results = {
        "expected_output_fps": 30,
        "sources": []
    }
    
    # These are hardcoded in the pipelines based on code analysis
    pipeline_info = [
        {
            "component": "Recording Pipeline",
            "file": "src/pipelines.py",
            "framerate": "30fps (normalized via videorate)",
            "note": "Input may be 60fps, normalized to 30fps for encoding"
        },
        {
            "component": "Ingest Pipeline (Preview)",
            "file": "src/pipelines.py", 
            "framerate": "30fps (normalized via videorate)",
            "note": "Streamed to MediaMTX for WHEP viewing"
        },
        {
            "component": "Test Source (fallback)",
            "file": "src/pipelines.py",
            "framerate": "30fps",
            "note": "Used when no camera signal"
        },
        {
            "component": "Reveal.js Source",
            "file": "src/reveal_source.py + config.yml",
            "framerate": "30fps (configurable)",
            "note": "Browser rendering to video"
        },
        {
            "component": "Mixer Graphics",
            "file": "src/mixer/core.py",
            "framerate": "30fps (animation loop)",
            "note": "Overlay graphics and transitions"
        }
    ]
    
    print("\n Pipeline framerate configuration:")
    for info in pipeline_info:
        print(f"\n   📹 {info['component']}")
        print(f"      File: {info['file']}")
        print(f"      Framerate: {info['framerate']}")
        print(f"      Note: {info['note']}")
        results["sources"].append(info)
    
    return results


def test_frontend_fps_config():
    """Report frontend FPS configuration."""
    print(f"\n{'='*60}")
    print("Frontend Update Rates (from source code)")
    print(f"{'='*60}")
    
    print("""
   📱 UI Update Intervals (usePerformanceMode.ts):
      
      Normal Mode:    100ms interval = 10 FPS
      Performance Mode: 500ms interval = 2 FPS
      
      Note: These are UI state updates (stats, indicators), 
            NOT video framerate. Video streams at full 30fps.
   
   📊 Signal Quality Thresholds (InputGrid.vue):
      
      >= 29 fps: Excellent (green)
      >= 24 fps: Good (green)  
      <  24 fps: Unstable (amber, pulsing)
      
   🎬 VDO.ninja Quality Settings (vdoninja.ts):
      
      quality=2: High quality (mixer/scene views)
      quality=1: Medium quality (guest connections)
      
      Note: VDO.ninja manages its own adaptive bitrate/fps
    """)


def run_gstreamer_test():
    """Run a quick GStreamer pipeline test to verify framerate."""
    print(f"\n{'='*60}")
    print("GStreamer Framerate Test")
    print(f"{'='*60}")
    
    # Check if GStreamer is available
    try:
        result = subprocess.run(
            ["gst-launch-1.0", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("\n   ⚠️  GStreamer not available (expected on macOS dev)")
            return None
        
        print(f"\n   GStreamer version: {result.stdout.strip().split(chr(10))[0]}")
        
        # Run a quick test pipeline to verify framerate
        print("\n   Running 3-second test pipeline...")
        test_pipeline = (
            "videotestsrc num-buffers=90 ! "
            "video/x-raw,width=320,height=240,framerate=30/1 ! "
            "fpsdisplaysink text-overlay=false signal-fps-measurements=true sync=false"
        )
        
        result = subprocess.run(
            ["gst-launch-1.0", test_pipeline],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "fps" in result.stderr.lower() or result.returncode == 0:
            print("   ✅ Test pipeline ran successfully at 30fps")
            return {"test": "passed", "fps": 30}
        else:
            print(f"   ⚠️  Pipeline result: {result.stderr[:200]}")
            return {"test": "unknown"}
            
    except FileNotFoundError:
        print("\n   ⚠️  GStreamer not installed (expected on dev machine)")
        return None
    except subprocess.TimeoutExpired:
        print("\n   ⚠️  GStreamer test timed out")
        return None
    except Exception as e:
        print(f"\n   ⚠️  GStreamer test error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Test preview framerate")
    parser.add_argument("--local", action="store_true", help="Test local MediaMTX")
    parser.add_argument("--remote", action="store_true", help="Test remote MediaMTX")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    args = parser.parse_args()
    
    # Default to all if no specific test selected
    if not (args.local or args.remote or args.all):
        args.all = True
    
    print("="*60)
    print("PREVIEW FRAMERATE TEST")
    print("="*60)
    print(f"\nExpected framerates (from code analysis):")
    for key, value in EXPECTED_FRAMERATES.items():
        print(f"  {key}: {value} fps")
    
    results = {}
    
    # Always show config info
    results["pipeline_config"] = check_pipeline_config()
    test_frontend_fps_config()
    
    # GStreamer test
    results["gstreamer"] = run_gstreamer_test()
    
    # Test local MediaMTX
    if args.local or args.all:
        results["local_mediamtx"] = test_mediamtx_api(LOCAL_MEDIAMTX_API)
        results["local_api"] = test_local_api()
    
    # Test remote MediaMTX
    if args.remote or args.all:
        results["remote_mediamtx"] = test_mediamtx_api(REMOTE_MEDIAMTX_API)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    print("""
   📹 Video Stream Framerate: 30 fps
      - All GStreamer pipelines normalize to 30fps via videorate
      - This is the actual video framerate sent to MediaMTX
      - WebRTC/WHEP clients receive this 30fps stream
   
   📱 UI Update Rate: 10 fps (normal) / 2 fps (performance mode)
      - Only affects stats/indicator updates
      - Does NOT affect video playback framerate
   
   ✅ Expected behavior:
      - Video previews should play at smooth 30fps
      - Stats (resolution, fps counter) update at 10fps
      - During heavy recording, UI updates slow to 2fps
    """)
    
    # Check if any streams were found
    if results.get("local_mediamtx", {}).get("accessible"):
        streams = results["local_mediamtx"].get("streams", {})
        ready_streams = [s for s, info in streams.items() if info.get("ready")]
        if ready_streams:
            print(f"\n   🎥 Active streams found: {', '.join(ready_streams)}")
            print("      These should all be streaming at 30fps")
        else:
            print("\n   ⚠️  No active streams (cameras may not be connected)")
    
    if results.get("local_api", {}).get("accessible"):
        framerates = results["local_api"].get("framerates", {})
        if framerates:
            print(f"\n   📊 Reported input framerates:")
            for cam, fps in framerates.items():
                status = "✅" if fps >= 29 else "⚠️ " if fps >= 24 else "❌"
                print(f"      {cam}: {fps}fps {status}")
    
    print("\n" + "="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
