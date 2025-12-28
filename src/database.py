"""SQLite database for scenes, queue, and file metadata."""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for scenes, queue, and file metadata."""
    
    def __init__(self, db_path: str = "data/app.db"):
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Scenes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    resolution_width INTEGER NOT NULL,
                    resolution_height INTEGER NOT NULL,
                    slots TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Queue table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position INTEGER NOT NULL,
                    scene_id TEXT NOT NULL,
                    duration INTEGER,
                    transition TEXT DEFAULT 'cut',
                    auto_advance BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Try to add auto_advance column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE queue ADD COLUMN auto_advance BOOLEAN DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column likely already exists
            
            # File metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    duration REAL,
                    width INTEGER,
                    height INTEGER,
                    loop BOOLEAN DEFAULT 0,
                    size_bytes INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()
    
    def migrate_json_scenes(self, scenes_dir: str) -> None:
        """Migrate JSON scene files to SQLite database.
        
        Args:
            scenes_dir: Directory containing JSON scene files
        """
        scenes_path = Path(scenes_dir)
        if not scenes_path.exists():
            return
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if migration already done
            cursor.execute("SELECT COUNT(*) FROM scenes")
            if cursor.fetchone()[0] > 0:
                logger.info("Scenes already in database, skipping migration")
                return
            
            # Load scenes from JSON files
            scene_files = list(scenes_path.glob("*.json"))
            for scene_file in scene_files:
                try:
                    with open(scene_file, "r") as f:
                        data = json.load(f)
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO scenes 
                        (id, label, resolution_width, resolution_height, slots)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        data["id"],
                        data["label"],
                        data["resolution"]["width"],
                        data["resolution"]["height"],
                        json.dumps(data["slots"])
                    ))
                    logger.info(f"Migrated scene: {data['id']}")
                except Exception as e:
                    logger.error(f"Failed to migrate scene from {scene_file}: {e}")
            
            conn.commit()
            logger.info(f"Migration complete: {len(scene_files)} scenes migrated")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # Scene methods
    def get_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get a scene by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "id": row["id"],
                "label": row["label"],
                "resolution": {
                    "width": row["resolution_width"],
                    "height": row["resolution_height"]
                },
                "slots": json.loads(row["slots"])
            }
        finally:
            conn.close()
    
    def list_scenes(self) -> List[Dict[str, Any]]:
        """List all scenes."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, label, resolution_width, resolution_height, slots FROM scenes")
            scenes = []
            for row in cursor.fetchall():
                slots = json.loads(row["slots"])
                scenes.append({
                    "id": row["id"],
                    "label": row["label"],
                    "resolution": {
                        "width": row["resolution_width"],
                        "height": row["resolution_height"]
                    },
                    "slot_count": len(slots)
                })
            return scenes
        finally:
            conn.close()
    
    def save_scene(self, scene_data: Dict[str, Any]) -> bool:
        """Save or update a scene."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scenes 
                (id, label, resolution_width, resolution_height, slots, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                scene_data["id"],
                scene_data["label"],
                scene_data["resolution"]["width"],
                scene_data["resolution"]["height"],
                json.dumps(scene_data["slots"])
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save scene: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_scene(self, scene_id: str) -> bool:
        """Delete a scene."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete scene: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # Queue methods
    def get_queue(self) -> List[Dict[str, Any]]:
        """Get current queue ordered by position."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, position, scene_id, duration, transition, auto_advance
                FROM queue 
                ORDER BY position
            """)
            return [
                {
                    "id": row["id"],
                    "position": row["position"],
                    "scene_id": row["scene_id"],
                    "duration": row["duration"],
                    "transition": row["transition"],
                    "auto_advance": bool(row["auto_advance"]) if "auto_advance" in row.keys() else False
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
    
    def save_queue(self, queue_items: List[Dict[str, Any]]) -> bool:
        """Save queue (replaces existing)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queue")
            for item in queue_items:
                cursor.execute("""
                    INSERT INTO queue (position, scene_id, duration, transition, auto_advance)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    item["position"],
                    item["scene_id"],
                    item.get("duration"),
                    item.get("transition", "cut"),
                    1 if item.get("auto_advance", False) else 0
                ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def clear_queue(self) -> bool:
        """Clear the queue."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queue")
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # File metadata methods
    def save_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """Save file metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO file_metadata 
                (id, file_path, file_type, duration, width, height, loop, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                metadata["file_path"],
                metadata["file_type"],
                metadata.get("duration"),
                metadata.get("width"),
                metadata.get("height"),
                1 if metadata.get("loop", False) else 0,
                metadata.get("size_bytes")
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save file metadata: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_metadata WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "id": row["id"],
                "file_path": row["file_path"],
                "file_type": row["file_type"],
                "duration": row["duration"],
                "width": row["width"],
                "height": row["height"],
                "loop": bool(row["loop"]),
                "size_bytes": row["size_bytes"],
                "created_at": row["created_at"]
            }
        finally:
            conn.close()
    
    def list_files(self) -> List[Dict[str, Any]]:
        """List all file metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_metadata ORDER BY created_at DESC")
            return [
                {
                    "id": row["id"],
                    "file_path": row["file_path"],
                    "file_type": row["file_type"],
                    "duration": row["duration"],
                    "width": row["width"],
                    "height": row["height"],
                    "loop": bool(row["loop"]),
                    "size_bytes": row["size_bytes"],
                    "created_at": row["created_at"]
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
    
    def delete_file_metadata(self, file_id: str) -> bool:
        """Delete file metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM file_metadata WHERE id = ?", (file_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete file metadata: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_file_metadata(self, file_id: str, updates: Dict[str, Any]) -> bool:
        """Update file metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            set_clauses = []
            values = []
            
            if "loop" in updates:
                set_clauses.append("loop = ?")
                values.append(1 if updates["loop"] else 0)
            
            if not set_clauses:
                return True
            
            values.append(file_id)
            cursor.execute(
                f"UPDATE file_metadata SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update file metadata: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

