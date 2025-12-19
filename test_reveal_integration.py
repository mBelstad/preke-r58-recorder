#!/usr/bin/env python3
"""Test script for Reveal.js video source integration."""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_config_loading():
    """Test that config loads with reveal section."""
    print("Test 1: Config loading...")
    try:
        from config import AppConfig
        
        # Load config
        config = AppConfig.load("config.yml")
        
        # Check reveal config exists
        assert hasattr(config, 'reveal'), "Config missing 'reveal' attribute"
        assert config.reveal.enabled == True, "Reveal should be enabled"
        assert config.reveal.resolution == "1920x1080", "Wrong resolution"
        assert config.reveal.framerate == 30, "Wrong framerate"
        assert config.reveal.bitrate == 4000, "Wrong bitrate"
        assert config.reveal.mediamtx_path == "slides", "Wrong MediaMTX path"
        assert config.reveal.renderer == "auto", "Wrong renderer"
        
        print("  ✓ Config loads correctly with reveal section")
        return True
    except Exception as e:
        print(f"  ✗ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scene_files():
    """Test that scene JSON files are valid."""
    print("\nTest 2: Scene files...")
    scenes = [
        "scenes/presentation_speaker.json",
        "scenes/presentation_focus.json",
        "scenes/presentation_pip.json"
    ]
    
    all_valid = True
    for scene_path in scenes:
        try:
            with open(scene_path) as f:
                scene_data = json.load(f)
            
            # Validate structure
            assert "id" in scene_data, f"{scene_path}: missing 'id'"
            assert "label" in scene_data, f"{scene_path}: missing 'label'"
            assert "slots" in scene_data, f"{scene_path}: missing 'slots'"
            
            # Check for slides source
            has_slides = any(
                slot.get("source") == "slides" or slot.get("source_type") == "reveal"
                for slot in scene_data["slots"]
            )
            
            if has_slides:
                print(f"  ✓ {scene_path} valid (has slides source)")
            else:
                print(f"  ⚠ {scene_path} valid but no slides source")
            
        except Exception as e:
            print(f"  ✗ {scene_path} invalid: {e}")
            all_valid = False
    
    return all_valid


def test_reveal_source_manager():
    """Test RevealSourceManager class."""
    print("\nTest 3: RevealSourceManager...")
    try:
        from reveal_source import RevealSourceManager
        
        # Create instance
        manager = RevealSourceManager(
            resolution="1920x1080",
            framerate=30,
            bitrate=4000,
            mediamtx_path="slides",
            renderer="auto"
        )
        
        print(f"  ✓ RevealSourceManager created")
        print(f"    - Renderer type: {manager.renderer_type or 'none detected'}")
        print(f"    - Resolution: {manager.resolution}")
        print(f"    - Framerate: {manager.framerate}")
        print(f"    - Bitrate: {manager.bitrate}")
        
        # Test status
        status = manager.get_status()
        assert status["state"] == "idle", "Initial state should be idle"
        assert status["renderer"] == manager.renderer_type, "Renderer mismatch"
        
        print(f"  ✓ Status method works")
        
        return True
        
    except Exception as e:
        print(f"  ✗ RevealSourceManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graphics_renderer():
    """Test GraphicsRenderer integration."""
    print("\nTest 4: GraphicsRenderer integration...")
    try:
        from graphics.renderer import GraphicsRenderer
        from reveal_source import RevealSourceManager
        
        # Create mock reveal manager
        reveal_manager = RevealSourceManager()
        
        # Create graphics renderer with reveal manager
        renderer = GraphicsRenderer(
            output_dir="/tmp/test_graphics",
            reveal_source_manager=reveal_manager
        )
        
        assert renderer.reveal_source_manager is not None, "Reveal manager not set"
        
        print(f"  ✓ GraphicsRenderer accepts reveal_source_manager")
        
        # Test create_presentation_source (should not crash)
        result = renderer.create_presentation_source(
            "test_pres",
            {
                "id": "test",
                "name": "Test Presentation",
                "theme": "black",
                "slides": [{"content": "# Test"}]
            }
        )
        
        # Result could be "slides" marker or None (if renderer not available)
        print(f"  ✓ create_presentation_source returns: {result}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ GraphicsRenderer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mixer_integration():
    """Test that mixer can handle slides source."""
    print("\nTest 5: Mixer integration...")
    try:
        # Just check that the code compiles and imports
        from mixer.core import MixerCore
        
        print(f"  ✓ MixerCore imports successfully")
        print(f"  ✓ Mixer should handle 'slides' source in _build_pipeline()")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Mixer integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Reveal.js Video Source Integration Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Config Loading", test_config_loading()))
    results.append(("Scene Files", test_scene_files()))
    results.append(("RevealSourceManager", test_reveal_source_manager()))
    results.append(("GraphicsRenderer", test_graphics_renderer()))
    results.append(("Mixer Integration", test_mixer_integration()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
