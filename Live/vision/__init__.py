"""
NIRA Live Multi-Room Vision Package.
Amazon Developer Hackathon 2026.
"""

from Live.vision.camera_models import (
    CameraConfig,
    CameraSourceType,
    CameraStatus,
    PostureType,
    RecoveryStatus,
    RoomState,
    TrackedPerson
)
from Live.vision.zone_session import ZoneSession
from Live.vision.room_tracker import RoomTracker
from Live.vision.camera_manager import CameraManager, get_camera_manager

__all__ = [
    "CameraConfig",
    "CameraSourceType",
    "CameraStatus",
    "PostureType",
    "RecoveryStatus",
    "RoomState",
    "TrackedPerson",
    "ZoneSession",
    "RoomTracker",
    "CameraManager",
    "get_camera_manager"
]
