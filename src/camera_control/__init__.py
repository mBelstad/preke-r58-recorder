"""Camera control module for external cameras."""
from .blackmagic import BlackmagicCamera
from .obsbot import ObsbotTail2
from .manager import CameraControlManager

__all__ = ["BlackmagicCamera", "ObsbotTail2", "CameraControlManager"]

