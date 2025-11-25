"""Scene queue management with auto-advance support."""
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class SceneQueue:
    """Manages scene queue with auto-advance functionality."""
    
    def __init__(self, database=None, on_advance: Optional[Callable[[str], None]] = None):
        """Initialize scene queue.
        
        Args:
            database: Database instance for persistence
            on_advance: Callback function called when queue advances (receives scene_id)
        """
        self.database = database
        self.on_advance = on_advance
        self.queue: List[Dict[str, Any]] = []
        self.current_position: int = 0
        self.auto_advance_enabled: bool = False
        self._queue_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        
        # Load queue from database
        self._load_queue()
    
    def _load_queue(self) -> None:
        """Load queue from database."""
        if self.database:
            try:
                self.queue = self.database.get_queue()
                # Sort by position
                self.queue.sort(key=lambda x: x["position"])
                logger.info(f"Loaded queue: {len(self.queue)} items")
            except Exception as e:
                logger.error(f"Failed to load queue: {e}")
    
    def _save_queue(self) -> None:
        """Save queue to database."""
        if self.database:
            try:
                self.database.save_queue(self.queue)
            except Exception as e:
                logger.error(f"Failed to save queue: {e}")
    
    def add(self, scene_id: str, duration: Optional[int] = None, transition: str = "cut", auto_advance: bool = False) -> bool:
        """Add scene to queue.
        
        Args:
            scene_id: Scene ID to add
            duration: Duration in seconds (for auto-advance)
            transition: Transition type ("cut", "auto", "mix")
            auto_advance: Whether to automatically advance after duration
        
        Returns:
            True if added successfully
        """
        with self._lock:
            position = len(self.queue)
            item = {
                "position": position,
                "scene_id": scene_id,
                "duration": duration,
                "transition": transition,
                "auto_advance": auto_advance
            }
            self.queue.append(item)
            self._save_queue()
            logger.info(f"Added scene to queue: {scene_id} at position {position}")
            return True

    def update(self, index: int, updates: Dict[str, Any]) -> bool:
        """Update queue item.
        
        Args:
            index: Index in queue list
            updates: Dictionary of fields to update
        
        Returns:
            True if updated successfully
        """
        with self._lock:
            if 0 <= index < len(self.queue):
                item = self.queue[index]
                item.update(updates)
                self._save_queue()
                logger.info(f"Updated queue item at index {index}: {updates}")
                return True
            return False

    def jump(self, index: int) -> Optional[str]:
        """Jump to specific position in queue and play it.
        
        Args:
            index: Index to jump to
            
        Returns:
            Scene ID if successful, None otherwise
        """
        with self._lock:
            if 0 <= index < len(self.queue):
                self.current_position = index
                # Trigger advance logic from this position
                return self.advance(force=True)
            return None
    
    def remove(self, index: int) -> bool:
        """Remove scene from queue by index.
        
        Args:
            index: Index in queue list
        
        Returns:
            True if removed successfully
        """
        with self._lock:
            if 0 <= index < len(self.queue):
                removed = self.queue.pop(index)
                # Reorder positions
                for i, item in enumerate(self.queue):
                    item["position"] = i
                self._save_queue()
                logger.info(f"Removed scene from queue at index {index}")
                return True
            return False
    
    def reorder(self, new_indices: List[int]) -> bool:
        """Reorder queue items.
        
        Args:
            new_indices: New order of indices (e.g., [2, 0, 1] to move item 2 to front)
        
        Returns:
            True if reordered successfully
        """
        with self._lock:
            if len(new_indices) != len(self.queue):
                return False
            
            # Create new queue in specified order
            new_queue = [self.queue[i] for i in new_indices]
            # Update positions
            for i, item in enumerate(new_queue):
                item["position"] = i
            self.queue = new_queue
            self._save_queue()
            logger.info("Queue reordered")
            return True
    
    def clear(self) -> bool:
        """Clear the queue."""
        with self._lock:
            self.queue = []
            self.current_position = 0
            self._stop_auto_advance()
            if self.database:
                self.database.clear_queue()
            logger.info("Queue cleared")
            return True
    
    def get_next(self) -> Optional[Dict[str, Any]]:
        """Get next scene in queue.
        
        Returns:
            Next queue item or None if queue is empty
        """
        with self._lock:
            if self.current_position >= len(self.queue):
                return None
            return self.queue[self.current_position]
    
    def advance(self, force: bool = False) -> Optional[str]:
        """Manually advance to next scene.
        
        Args:
            force: If True, play current_position even if not advanced
        
        Returns:
            Next scene_id or None if queue is empty
        """
        with self._lock:
            if self.current_position >= len(self.queue):
                logger.info("Queue completed")
                return None
            
            # If force is true, we play current position. Otherwise increment first.
            # Wait, advance() usually means "go to next".
            # If force=True (jump), we set current_position before calling this.
            # So if force=True, we shouldn't increment.
            if not force:
                # Increment logic: check if we are starting or continuing
                # If we just started, current_position is 0. Should we play 0?
                # Usually "Advance" means "Next".
                # Let's assume current_position points to the NEXT item to play.
                pass
            
            # But wait, if we play item 0, then current_position should become 1.
            # So we get item at current_position, then increment.
            
            item = self.queue[self.current_position]
            scene_id = item["scene_id"]
            
            # Increment for next time
            self.current_position += 1
            
            # Schedule next advance if item has auto_advance enabled
            # We don't check global auto_advance_enabled here necessarily, unless we want a global kill switch.
            # User asked for per-item setting. Let's respect item setting.
            # But maybe keep global toggle as a master switch?
            # User said "Auto advance ... should be able to activate for each element".
            # I'll make item setting override, or require both? Usually item setting is enough if "Auto Advance" button is gone.
            # Let's use item["auto_advance"] primarily.
            
            if item.get("auto_advance", False) and self.current_position < len(self.queue):
                duration = item.get("duration", 10)
                self._schedule_advance(duration)
            else:
                self._stop_auto_advance()
            
            logger.info(f"Queue advanced to position {self.current_position}: {scene_id}")
            return scene_id
    
    def start_auto_advance(self) -> bool:
        """Start auto-advance mode."""
        with self._lock:
            if self.auto_advance_enabled:
                return True
            
            self.auto_advance_enabled = True
            
            # If we have a current item, schedule its advance
            if self.current_position < len(self.queue):
                item = self.queue[self.current_position]
                duration = item.get("duration", 10)
                self._schedule_advance(duration)
            
            logger.info("Auto-advance started")
            return True
    
    def stop_auto_advance(self) -> bool:
        """Stop auto-advance mode."""
        with self._lock:
            if not self.auto_advance_enabled:
                return True
            
            self._stop_auto_advance()
            logger.info("Auto-advance stopped")
            return True
    
    def _schedule_advance(self, duration: int) -> None:
        """Schedule next queue advance."""
        self._stop_auto_advance()  # Cancel any existing timer
        
        def advance_callback():
            scene_id = self.advance()
            if scene_id and self.on_advance:
                self.on_advance(scene_id)
        
        self._queue_timer = threading.Timer(duration, advance_callback)
        self._queue_timer.start()
        logger.debug(f"Scheduled queue advance in {duration} seconds")
    
    def _stop_auto_advance(self) -> None:
        """Stop auto-advance timer."""
        if self._queue_timer:
            self._queue_timer.cancel()
            self._queue_timer = None
        self.auto_advance_enabled = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get queue status."""
        with self._lock:
            return {
                "queue_length": len(self.queue),
                "current_position": self.current_position,
                "auto_advance_enabled": self.auto_advance_enabled,
                "current_item": self.queue[self.current_position] if self.current_position < len(self.queue) else None
            }
    
    def reset_position(self) -> None:
        """Reset queue position to start."""
        with self._lock:
            self.current_position = 0
            self._stop_auto_advance()

