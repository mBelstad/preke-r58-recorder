"""Tests for scene management."""
import unittest
from pathlib import Path
import tempfile
import shutil
import json

from src.mixer.scenes import SceneManager, Scene, SceneSlot


class TestSceneManager(unittest.TestCase):
    """Test SceneManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.scene_manager = SceneManager(scenes_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_default_scenes_created(self):
        """Test that default scenes are created."""
        scenes = self.scene_manager.list_scenes()
        self.assertGreater(len(scenes), 0)
        
        # Check for expected default scenes
        scene_ids = [s["id"] for s in scenes]
        self.assertIn("quad", scene_ids)
        self.assertIn("two_up", scene_ids)
        self.assertIn("cam0_full", scene_ids)

    def test_get_scene(self):
        """Test getting a scene by ID."""
        scene = self.scene_manager.get_scene("quad")
        self.assertIsNotNone(scene)
        self.assertEqual(scene.id, "quad")
        self.assertEqual(len(scene.slots), 4)

    def test_scene_coordinates(self):
        """Test relative to absolute coordinate conversion."""
        scene = self.scene_manager.get_scene("quad")
        self.assertIsNotNone(scene)
        
        # Check first slot (top-left)
        slot = scene.slots[0]
        coords = scene.get_absolute_coords(slot)
        
        # Quad scene: each slot is 0.5x0.5, starting at (0,0)
        self.assertEqual(coords["x"], 0)
        self.assertEqual(coords["y"], 0)
        self.assertEqual(coords["w"], 960)  # 1920 * 0.5
        self.assertEqual(coords["h"], 540)  # 1080 * 0.5

    def test_create_scene(self):
        """Test creating a new scene."""
        new_scene = Scene(
            id="test_scene",
            label="Test Scene",
            resolution={"width": 1920, "height": 1080},
            slots=[
                SceneSlot(source="cam0", x_rel=0.0, y_rel=0.0, w_rel=1.0, h_rel=1.0)
            ]
        )
        
        success = self.scene_manager.create_scene(new_scene)
        self.assertTrue(success)
        
        # Verify scene was saved
        scene_file = Path(self.temp_dir) / "test_scene.json"
        self.assertTrue(scene_file.exists())
        
        # Verify scene can be loaded
        loaded = self.scene_manager.get_scene("test_scene")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, "test_scene")

    def test_scene_serialization(self):
        """Test scene JSON serialization."""
        scene = self.scene_manager.get_scene("quad")
        scene_dict = scene.to_dict()
        
        # Verify it's valid JSON
        json_str = json.dumps(scene_dict)
        self.assertIsInstance(json_str, str)
        
        # Verify it can be deserialized
        loaded = Scene.from_dict(json.loads(json_str))
        self.assertEqual(loaded.id, scene.id)
        self.assertEqual(len(loaded.slots), len(scene.slots))


if __name__ == "__main__":
    unittest.main()

