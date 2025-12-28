"""File management for uploaded videos and images."""
import logging
import uuid
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import mimetypes

logger = logging.getLogger(__name__)

# Supported file types
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


class FileManager:
    """Manages uploaded video and image files."""
    
    def __init__(self, uploads_dir: str = "uploads", database=None):
        """Initialize file manager.
        
        Args:
            uploads_dir: Base directory for uploads
            database: Database instance for metadata storage
        """
        self.uploads_dir = Path(uploads_dir)
        self.videos_dir = self.uploads_dir / "videos"
        self.images_dir = self.uploads_dir / "images"
        self.database = database
        
        # Create directories
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_type(self, filename: str) -> Optional[str]:
        """Determine file type from extension."""
        ext = Path(filename).suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            return "video"
        elif ext in IMAGE_EXTENSIONS:
            return "image"
        return None
    
    def _validate_file(self, filename: str) -> tuple[bool, Optional[str]]:
        """Validate file type.
        
        Returns:
            (is_valid, error_message)
        """
        file_type = self._get_file_type(filename)
        if not file_type:
            return False, f"Unsupported file type. Supported: {', '.join(VIDEO_EXTENSIONS | IMAGE_EXTENSIONS)}"
        return True, None
    
    def save_file(self, file_content: bytes, filename: str, loop: bool = False) -> Dict[str, Any]:
        """Save uploaded file.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            loop: Whether video should loop (for videos only)
        
        Returns:
            File metadata dictionary
        """
        # Validate file type
        is_valid, error = self._validate_file(filename)
        if not is_valid:
            raise ValueError(error)
        
        file_type = self._get_file_type(filename)
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        
        # Determine save directory
        save_dir = self.videos_dir if file_type == "video" else self.images_dir
        file_path = save_dir / f"{file_id}{ext}"
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Get file metadata
        size_bytes = len(file_content)
        
        # For videos, we'd need to probe with GStreamer to get duration/resolution
        # For now, we'll set defaults and update later if needed
        metadata = {
            "id": file_id,
            "file_path": str(file_path),
            "file_type": file_type,
            "duration": None,  # Will be set when probed
            "width": None,
            "height": None,
            "loop": loop if file_type == "video" else False,
            "size_bytes": size_bytes
        }
        
        # Save to database if available
        if self.database:
            self.database.save_file_metadata(file_id, metadata)
        
        logger.info(f"Saved {file_type} file: {file_id} ({filename})")
        return metadata
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get file path by ID."""
        if self.database:
            metadata = self.database.get_file_metadata(file_id)
            if metadata:
                return Path(metadata["file_path"])
        return None
    
    def list_files(self) -> List[Dict[str, Any]]:
        """List all uploaded files."""
        if self.database:
            return self.database.list_files()
        return []
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata."""
        if self.database:
            return self.database.get_file_metadata(file_id)
        return None
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file and its metadata."""
        # Get metadata first
        metadata = self.get_file_metadata(file_id)
        if not metadata:
            return False
        
        # Delete file
        file_path = Path(metadata["file_path"])
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
                return False
        
        # Delete metadata from database
        if self.database:
            self.database.delete_file_metadata(file_id)
        
        logger.info(f"Deleted file: {file_id}")
        return True
    
    def update_file_settings(self, file_id: str, settings: Dict[str, Any]) -> bool:
        """Update file settings (e.g., loop)."""
        if self.database:
            return self.database.update_file_metadata(file_id, settings)
        return False

