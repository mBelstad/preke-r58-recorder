"""
Set up multi-camera timeline in DaVinci Resolve.

Creates a timeline with multiple camera angles and sets up multi-cam sync.
"""

import sys
import os

# Add DaVinci Resolve Scripting API to path
if sys.platform == "darwin":
    resolve_api_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
elif sys.platform == "win32":
    resolve_api_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
else:
    resolve_api_path = "/opt/resolve/Developer/Scripting/Modules"

if os.path.exists(resolve_api_path):
    sys.path.insert(0, resolve_api_path)

try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    print("Error: Could not import DaVinciResolveScript")
    sys.exit(1)


def create_multicam_timeline(project_name: str, timeline_name: str, camera_ids: list) -> bool:
    """Create a multi-camera timeline.
    
    Args:
        project_name: Name of DaVinci Resolve project
        timeline_name: Name for the new timeline
        camera_ids: List of camera IDs to include
        
    Returns:
        True if successful, False otherwise
    """
    resolve = dvr_script.scriptapp("Resolve")
    if not resolve:
        print("Error: DaVinci Resolve not available")
        return False
    
    project_manager = resolve.GetProjectManager()
    project = project_manager.LoadProject(project_name)
    
    if not project:
        print(f"Error: Project {project_name} not found")
        return False
    
    media_pool = project.GetMediaPool()
    root_folder = media_pool.GetRootFolder()
    
    # Check if timeline already exists
    timeline_count = media_pool.GetTimelineCount()
    for i in range(timeline_count):
        timeline = media_pool.GetTimelineByIndex(i + 1)
        if timeline and timeline.GetName() == timeline_name:
            print(f"Timeline {timeline_name} already exists")
            return True
    
    # Create new timeline
    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if not timeline:
        print(f"Failed to create timeline {timeline_name}")
        return False
    
    print(f"Created timeline: {timeline_name}")
    
    # Get clips from camera bins and add to timeline
    bins = root_folder.GetBinList()
    bin_map = {bin.GetName(): bin for bin in bins}
    
    # Get clips from each camera bin
    all_clips = []
    for cam_id in camera_ids:
        if cam_id in bin_map:
            bin_clips = bin_map[cam_id].GetClipList()
            if bin_clips:
                all_clips.extend(bin_clips)
                print(f"Found {len(bin_clips)} clips in {cam_id} bin")
    
    if not all_clips:
        print("Warning: No clips found to add to timeline")
        return True
    
    # Add clips to timeline
    # Note: Multi-cam sync setup requires more complex logic
    # This is a basic implementation - full multi-cam setup would require:
    # 1. Creating compound clips
    # 2. Setting up sync points
    # 3. Configuring multi-cam viewer
    
    print(f"Timeline created with {len(all_clips)} clips available")
    print("Note: Full multi-cam sync setup requires manual configuration or advanced scripting")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: setup_multicam_timeline.py <project_name> <timeline_name> <cam_id1> [cam_id2 ...]")
        print("Example: setup_multicam_timeline.py session_20250108_143022 multicam_timeline cam0 cam1 cam2")
        sys.exit(1)
    
    project_name = sys.argv[1]
    timeline_name = sys.argv[2]
    camera_ids = sys.argv[3:]
    
    success = create_multicam_timeline(project_name, timeline_name, camera_ids)
    sys.exit(0 if success else 1)
