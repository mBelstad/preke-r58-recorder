#!/usr/bin/env python3
"""
Recreate scenes for R58 switcher.
Deletes all existing scenes and creates a proper production set using cam1, cam2, cam3.
(cam0 is excluded as it has no HDMI connection)
"""

import requests
import json
import sys

API_BASE = "http://127.0.0.1:8000"

# Scene definitions
SCENES = [
    # Fullscreen scenes
    {
        "id": "cam1_full",
        "label": "Camera 1",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 1.0,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    {
        "id": "cam2_full",
        "label": "Camera 2",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 1.0,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    {
        "id": "cam3_full",
        "label": "Camera 3",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam3",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 1.0,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    # Split layouts
    {
        "id": "two_up",
        "label": "2-Up Side by Side",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 0.5,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.5,
                "y_rel": 0.0,
                "w_rel": 0.5,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    {
        "id": "three_up",
        "label": "3-Up Equal",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 0.333,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.333,
                "y_rel": 0.0,
                "w_rel": 0.334,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam3",
                "source_type": "camera",
                "x_rel": 0.667,
                "y_rel": 0.0,
                "w_rel": 0.333,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    {
        "id": "top_bottom",
        "label": "Top-Bottom Split",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 1.0,
                "h_rel": 0.5,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.5,
                "w_rel": 1.0,
                "h_rel": 0.5,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    {
        "id": "interview",
        "label": "Interview",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 0.5,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam3",
                "source_type": "camera",
                "x_rel": 0.5,
                "y_rel": 0.0,
                "w_rel": 0.5,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    # Picture-in-Picture
    {
        "id": "pip_cam1_main",
        "label": "PiP: Camera 1 + 2",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 1.0,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.72,
                "y_rel": 0.72,
                "w_rel": 0.25,
                "h_rel": 0.25,
                "z": 1,
                "alpha": 1.0
            }
        ]
    },
    {
        "id": "pip_cam2_main",
        "label": "PiP: Camera 2 + 3",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 1.0,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam3",
                "source_type": "camera",
                "x_rel": 0.72,
                "y_rel": 0.72,
                "w_rel": 0.25,
                "h_rel": 0.25,
                "z": 1,
                "alpha": 1.0
            }
        ]
    },
    # Presenter layouts
    {
        "id": "main_two_side",
        "label": "Main + 2 Side",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 0.66,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.66,
                "y_rel": 0.0,
                "w_rel": 0.34,
                "h_rel": 0.5,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam3",
                "source_type": "camera",
                "x_rel": 0.66,
                "y_rel": 0.5,
                "w_rel": 0.34,
                "h_rel": 0.5,
                "z": 0,
                "alpha": 1.0
            }
        ]
    },
    {
        "id": "speaker_focus",
        "label": "Speaker Focus",
        "resolution": {"width": 1920, "height": 1080},
        "slots": [
            {
                "source": "cam1",
                "source_type": "camera",
                "x_rel": 0.0,
                "y_rel": 0.0,
                "w_rel": 0.75,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            },
            {
                "source": "cam2",
                "source_type": "camera",
                "x_rel": 0.75,
                "y_rel": 0.0,
                "w_rel": 0.25,
                "h_rel": 1.0,
                "z": 0,
                "alpha": 1.0
            }
        ]
    }
]


def delete_all_scenes():
    """Delete all existing scenes."""
    print("Fetching existing scenes...")
    try:
        response = requests.get(f"{API_BASE}/api/scenes", timeout=5)
        response.raise_for_status()
        data = response.json()
        scenes = data.get("scenes", [])
        
        print(f"Found {len(scenes)} existing scenes")
        
        for scene in scenes:
            scene_id = scene["id"]
            print(f"  Deleting scene: {scene_id} ({scene.get('label', 'N/A')})")
            try:
                del_response = requests.delete(f"{API_BASE}/api/scenes/{scene_id}", timeout=5)
                if del_response.status_code == 200:
                    print(f"    ✓ Deleted {scene_id}")
                else:
                    print(f"    ✗ Failed to delete {scene_id}: {del_response.status_code}")
            except Exception as e:
                print(f"    ✗ Error deleting {scene_id}: {e}")
        
        print(f"Deleted {len(scenes)} scenes")
        return True
    except Exception as e:
        print(f"Error fetching scenes: {e}")
        return False


def create_scenes():
    """Create new production scenes."""
    print(f"\nCreating {len(SCENES)} new scenes...")
    
    created = 0
    failed = 0
    
    for scene in SCENES:
        scene_id = scene["id"]
        label = scene["label"]
        print(f"  Creating scene: {scene_id} ({label})")
        
        try:
            response = requests.post(
                f"{API_BASE}/api/scenes",
                json=scene,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"    ✓ Created {scene_id}")
                created += 1
            else:
                print(f"    ✗ Failed to create {scene_id}: {response.status_code}")
                print(f"      Response: {response.text}")
                failed += 1
        except Exception as e:
            print(f"    ✗ Error creating {scene_id}: {e}")
            failed += 1
    
    print(f"\nCreated {created} scenes, {failed} failed")
    return failed == 0


def main():
    print("=" * 60)
    print("R58 Scene Recreation Script")
    print("=" * 60)
    print()
    
    # Delete all existing scenes
    if not delete_all_scenes():
        print("\n✗ Failed to delete existing scenes")
        sys.exit(1)
    
    # Create new scenes
    if not create_scenes():
        print("\n✗ Some scenes failed to create")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ Scene recreation completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

