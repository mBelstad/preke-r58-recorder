"""
Import media files into DaVinci Resolve Media Pool, organized by camera.

This script handles importing files into appropriate bins based on camera ID.
"""

import sys
import os
from pathlib import Path

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


def import_media_to_bins(project_name: str, file_paths: dict) -> bool:
    """Import media files into camera-specific bins.
    
    Args:
        project_name: Name of DaVinci Resolve project
        file_paths: Dictionary mapping camera IDs to file paths
                   e.g., {"cam0": "/path/to/file.mkv", "cam1": "/path/to/file2.mkv"}
    
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
    
    # Get existing bins
    bins = root_folder.GetBinList()
    bin_map = {bin.GetName(): bin for bin in bins}
    
    imported_count = 0
    failed_count = 0
    
    for cam_id, file_path in file_paths.items():
        if not file_path:
            continue
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}")
            failed_count += 1
            continue
        
        # Get or create bin for this camera
        if cam_id in bin_map:
            target_bin = bin_map[cam_id]
        else:
            # Create new bin
            target_bin = media_pool.AddSubFolder(root_folder, cam_id)
            if target_bin:
                bin_map[cam_id] = target_bin
                print(f"Created bin: {cam_id}")
            else:
                print(f"Warning: Failed to create bin for {cam_id}, using root folder")
                target_bin = root_folder
        
        # Import file
        result = media_pool.ImportMedia([str(file_path)], target_bin)
        if result:
            print(f"Imported {file_path.name} to {cam_id} bin")
            imported_count += 1
        else:
            print(f"Failed to import {file_path.name}")
            failed_count += 1
    
    print(f"Import complete: {imported_count} succeeded, {failed_count} failed")
    return imported_count > 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: import_media.py <project_name> <cam_id:file_path> [cam_id:file_path ...]")
        print("Example: import_media.py session_20250108_143022 cam0:/path/to/cam0.mkv cam1:/path/to/cam1.mkv")
        sys.exit(1)
    
    project_name = sys.argv[1]
    file_paths = {}
    
    for arg in sys.argv[2:]:
        if ':' in arg:
            cam_id, file_path = arg.split(':', 1)
            file_paths[cam_id] = file_path
        else:
            print(f"Warning: Invalid argument format: {arg} (expected cam_id:file_path)")
    
    success = import_media_to_bins(project_name, file_paths)
    sys.exit(0 if success else 1)
