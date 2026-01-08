#!/usr/bin/env python3
"""
DaVinci Resolve Automation Service

Listens for webhooks from R58 recording system and automatically:
- Creates DaVinci Resolve projects
- Imports media files organized by camera
- Sets up multi-camera timelines
- Handles incremental file imports

Run this on your editing PC (Mac or Windows) with DaVinci Resolve Studio installed.
"""

import sys
import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add DaVinci Resolve Scripting API to path
# macOS path
if sys.platform == "darwin":
    resolve_api_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
# Windows path
elif sys.platform == "win32":
    resolve_api_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
# Linux path
else:
    resolve_api_path = "/opt/resolve/Developer/Scripting/Modules"

if os.path.exists(resolve_api_path):
    sys.path.insert(0, resolve_api_path)
else:
    print(f"Warning: DaVinci Resolve Scripting API not found at {resolve_api_path}")
    print("Please ensure DaVinci Resolve Studio is installed.")

try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    print("Error: Could not import DaVinciResolveScript")
    print("Please ensure DaVinci Resolve Studio is installed and the Scripting API is available.")
    sys.exit(1)

# Web server for webhooks
try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Error: Flask not installed. Install with: pip install flask")
    sys.exit(1)

# File watching for incremental imports
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("Warning: watchdog not installed. Incremental file watching disabled.")
    print("Install with: pip install watchdog")
    Observer = None
    FileSystemEventHandler = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global state
active_sessions: Dict[str, Dict[str, Any]] = {}
resolve = None


def get_resolve():
    """Get DaVinci Resolve instance."""
    global resolve
    if resolve is None:
        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            logger.error("Failed to connect to DaVinci Resolve. Is it running?")
            return None
    return resolve


class SessionManager:
    """Manages DaVinci Resolve projects for recording sessions."""
    
    def __init__(self):
        self.projects: Dict[str, Any] = {}  # session_id -> project
        self.timelines: Dict[str, Any] = {}  # session_id -> timeline
        self.media_pools: Dict[str, Any] = {}  # session_id -> media_pool
    
    def create_project(self, session_id: str, template: Optional[str] = None) -> Optional[Any]:
        """Create a new DaVinci Resolve project for a session."""
        resolve = get_resolve()
        if not resolve:
            return None
        
        project_manager = resolve.GetProjectManager()
        
        # Check if project already exists
        project = project_manager.LoadProject(session_id)
        if project:
            logger.info(f"Project {session_id} already exists, using existing")
            self.projects[session_id] = project
            return project
        
        # Create new project
        project = project_manager.CreateProject(session_id)
        if not project:
            logger.error(f"Failed to create project {session_id}")
            return None
        
        logger.info(f"Created DaVinci Resolve project: {session_id}")
        self.projects[session_id] = project
        
        # Apply template if specified
        if template:
            self._apply_template(project, template)
        
        return project
    
    def _apply_template(self, project: Any, template_name: str):
        """Apply a project template (placeholder for future implementation)."""
        # TODO: Implement template loading
        logger.debug(f"Template {template_name} would be applied (not yet implemented)")
    
    def get_media_pool(self, session_id: str) -> Optional[Any]:
        """Get media pool for a session's project."""
        if session_id not in self.projects:
            return None
        
        project = self.projects[session_id]
        media_pool = project.GetMediaPool()
        self.media_pools[session_id] = media_pool
        return media_pool
    
    def create_camera_bins(self, session_id: str, camera_ids: List[str]) -> bool:
        """Create bins for each camera."""
        media_pool = self.get_media_pool(session_id)
        if not media_pool:
            return False
        
        root_folder = media_pool.GetRootFolder()
        
        for cam_id in camera_ids:
            # Check if bin already exists
            bins = root_folder.GetBinList()
            bin_exists = any(bin.GetName() == cam_id for bin in bins)
            
            if not bin_exists:
                new_bin = media_pool.AddSubFolder(root_folder, cam_id)
                if new_bin:
                    logger.info(f"Created bin for {cam_id}")
                else:
                    logger.warning(f"Failed to create bin for {cam_id}")
        
        return True
    
    def import_media(self, session_id: str, file_paths: Dict[str, str]) -> bool:
        """Import media files into appropriate camera bins."""
        media_pool = self.get_media_pool(session_id)
        if not media_pool:
            return False
        
        root_folder = media_pool.GetRootFolder()
        bins = root_folder.GetBinList()
        bin_map = {bin.GetName(): bin for bin in bins}
        
        imported_count = 0
        for cam_id, file_path in file_paths.items():
            if not file_path or not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path} for {cam_id}")
                continue
            
            # Get target bin
            target_bin = bin_map.get(cam_id, root_folder)
            
            # Import file
            result = media_pool.ImportMedia([file_path], target_bin)
            if result:
                logger.info(f"Imported {file_path} to {cam_id} bin")
                imported_count += 1
            else:
                logger.warning(f"Failed to import {file_path} to {cam_id} bin")
        
        logger.info(f"Imported {imported_count} files for session {session_id}")
        return imported_count > 0
    
    def create_multicam_timeline(self, session_id: str, camera_ids: List[str]) -> Optional[Any]:
        """Create a multi-camera timeline."""
        media_pool = self.get_media_pool(session_id)
        if not media_pool:
            return None
        
        timeline_name = f"{session_id}_multicam"
        
        # Check if timeline already exists
        timelines = media_pool.GetTimelineCount()
        for i in range(timelines):
            timeline = media_pool.GetTimelineByIndex(i + 1)
            if timeline and timeline.GetName() == timeline_name:
                logger.info(f"Timeline {timeline_name} already exists")
                self.timelines[session_id] = timeline
                return timeline
        
        # Create new timeline
        timeline = media_pool.CreateEmptyTimeline(timeline_name)
        if not timeline:
            logger.error(f"Failed to create timeline {timeline_name}")
            return None
        
        logger.info(f"Created timeline: {timeline_name}")
        self.timelines[session_id] = timeline
        
        # TODO: Add clips to timeline and set up multi-cam sync
        # This requires more complex logic to:
        # 1. Get clips from bins
        # 2. Add to timeline tracks
        # 3. Set up multi-cam sync
        
        return timeline


session_manager = SessionManager()


class FileWatcher(FileSystemEventHandler):
    """Watches for new files in recording directories."""
    
    def __init__(self, session_id: str, camera_id: str, recording_dir: str):
        self.session_id = session_id
        self.camera_id = camera_id
        self.recording_dir = recording_dir
        self.processed_files = set()
    
    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if file_path in self.processed_files:
            return
        
        # Wait a bit for file to be fully written
        import time
        time.sleep(2)
        
        if os.path.exists(file_path) and file_path.endswith('.mkv'):
            self.processed_files.add(file_path)
            logger.info(f"New file detected: {file_path}")
            
            # Import to DaVinci
            media_pool = session_manager.get_media_pool(self.session_id)
            if media_pool:
                root_folder = media_pool.GetRootFolder()
                bins = root_folder.GetBinList()
                bin_map = {bin.GetName(): bin for bin in bins}
                target_bin = bin_map.get(self.camera_id, root_folder)
                
                result = media_pool.ImportMedia([file_path], target_bin)
                if result:
                    logger.info(f"Auto-imported new file: {file_path}")
                else:
                    logger.warning(f"Failed to auto-import: {file_path}")


@app.route('/webhook/session-start', methods=['POST'])
def handle_session_start():
    """Handle session start webhook."""
    try:
        data = request.json
        event = data.get('event')
        session_id = data.get('session_id')
        start_time = data.get('start_time')
        cameras = data.get('cameras', {})
        file_paths = data.get('file_paths', {})
        
        logger.info(f"Received session_start webhook for {session_id}")
        
        # Create project
        project = session_manager.create_project(session_id)
        if not project:
            return jsonify({"error": "Failed to create project"}), 500
        
        # Create camera bins
        camera_ids = list(cameras.keys())
        session_manager.create_camera_bins(session_id, camera_ids)
        
        # Import initial files
        session_manager.import_media(session_id, file_paths)
        
        # Create multi-cam timeline if configured
        # (Check config from webhook or use default)
        create_timeline = data.get('create_multicam_timeline', True)
        if create_timeline and len(camera_ids) > 1:
            session_manager.create_multicam_timeline(session_id, camera_ids)
        
        # Store session info
        active_sessions[session_id] = {
            'session_id': session_id,
            'start_time': start_time,
            'cameras': cameras,
            'file_paths': file_paths
        }
        
        # Set up file watchers for incremental imports
        if Observer and FileSystemEventHandler:
            # Extract recording directories from file paths
            for cam_id, file_path in file_paths.items():
                if file_path:
                    recording_dir = str(Path(file_path).parent)
                    observer = Observer()
                    handler = FileWatcher(session_id, cam_id, recording_dir)
                    observer.schedule(handler, recording_dir, recursive=False)
                    observer.start()
                    active_sessions[session_id].setdefault('observers', []).append(observer)
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "project_created": True
        }), 200
    
    except Exception as e:
        logger.error(f"Error handling session_start webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/webhook/session-stop', methods=['POST'])
def handle_session_stop():
    """Handle session stop webhook."""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        logger.info(f"Received session_stop webhook for {session_id}")
        
        # Stop file watchers
        if session_id in active_sessions:
            observers = active_sessions[session_id].get('observers', [])
            for observer in observers:
                observer.stop()
                observer.join()
        
        # Remove from active sessions
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        return jsonify({
            "status": "success",
            "session_id": session_id
        }), 200
    
    except Exception as e:
        logger.error(f"Error handling session_stop webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/webhook/file-added', methods=['POST'])
def handle_file_added():
    """Handle file added webhook for incremental imports."""
    try:
        data = request.json
        session_id = data.get('session_id')
        cam_id = data.get('cam_id')
        file_path = data.get('file_path')
        
        logger.info(f"Received file_added webhook: {file_path} for {cam_id}")
        
        # Import file to appropriate bin
        media_pool = session_manager.get_media_pool(session_id)
        if media_pool:
            root_folder = media_pool.GetRootFolder()
            bins = root_folder.GetBinList()
            bin_map = {bin.GetName(): bin for bin in bins}
            target_bin = bin_map.get(cam_id, root_folder)
            
            result = media_pool.ImportMedia([file_path], target_bin)
            if result:
                logger.info(f"Imported new file: {file_path}")
            else:
                logger.warning(f"Failed to import: {file_path}")
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        logger.error(f"Error handling file_added webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    resolve = get_resolve()
    return jsonify({
        "status": "healthy",
        "davinci_connected": resolve is not None,
        "active_sessions": len(active_sessions)
    }), 200


if __name__ == '__main__':
    # Check DaVinci Resolve connection
    resolve = get_resolve()
    if not resolve:
        logger.error("Cannot start: DaVinci Resolve not available")
        sys.exit(1)
    
    logger.info("DaVinci Resolve Automation Service starting...")
    logger.info("Webhook endpoints:")
    logger.info("  POST /webhook/session-start")
    logger.info("  POST /webhook/session-stop")
    logger.info("  POST /webhook/file-added")
    logger.info("  GET  /health")
    
    # Run Flask server
    app.run(host='0.0.0.0', port=8080, debug=False)
