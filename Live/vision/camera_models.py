"""
Data models for NIRA Multi-Room Vision and Camera Tracking.
Amazon Developer Hackathon 2026.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from Live.core.models import ZoneType, SeverityLevel
from Live.core.time_provider import get_time_provider


class CameraSourceType(str, Enum):
    BROWSER = "browser"
    USB = "usb"
    RTSP = "rtsp"
    VIDEO_FILE = "video_file"


class CameraStatus(str, Enum):
    ONLINE = "ONLINE"
    STARTING = "STARTING"
    STOPPED = "STOPPED"
    OFFLINE = "OFFLINE"
    FRAME_STALE = "FRAME_STALE"
    MODEL_ERROR = "MODEL_ERROR"
    FRAME_ERROR = "FRAME_ERROR"


class PostureType(str, Enum):
    UPRIGHT = "UPRIGHT"
    STANDING = "STANDING"
    WALKING = "WALKING"
    SITTING = "SITTING"
    SLUMPED = "SLUMPED"
    LYING_BED = "LYING_BED"
    LYING_FLOOR = "LYING_FLOOR"
    FALL_CANDIDATE = "FALL_CANDIDATE"
    UNKNOWN = "UNKNOWN"


class RecoveryStatus(str, Enum):
    NONE = "NONE"
    MONITORING_RECOVERY = "MONITORING_RECOVERY"
    RECOVERY_MOVEMENT = "RECOVERY_MOVEMENT"
    PERSISTENT_FLOOR_POSTURE = "PERSISTENT_FLOOR_POSTURE"
    RECOVERED_STANDING = "RECOVERED_STANDING"


class CameraConfig(BaseModel):
    """Configuration for an individual room camera (Phase 2)."""
    model_config = ConfigDict(extra="ignore")

    camera_id: str
    room_id: ZoneType
    room_name: str
    source_type: CameraSourceType = CameraSourceType.BROWSER
    source_config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    device_index: Optional[int] = None
    rtsp_url: Optional[str] = None


class TrackedPerson(BaseModel):
    """Represents a person detected and tracked within a camera view (Phases 10, 11)."""
    model_config = ConfigDict(extra="ignore")

    track_id: int
    is_resident: bool = True
    confidence: float = 0.9
    bbox: List[float] = Field(default_factory=list)  # [x1, y1, x2, y2]
    centroid: List[float] = Field(default_factory=list)  # [cx, cy]
    torso_angle_deg: float = 0.0
    posture: PostureType = PostureType.STANDING
    activity: str = "WALKING"
    movement_velocity: float = 0.5
    last_seen_timestamp: float = Field(default_factory=lambda: get_time_provider().time())


class RoomState(BaseModel):
    """Authoritative independent state for each room camera (Phases 4, 42)."""
    model_config = ConfigDict(extra="ignore")

    room_id: ZoneType
    room_name: str
    camera_id: str
    camera_status: CameraStatus = CameraStatus.ONLINE
    model_status: str = "READY"
    person_present: bool = False
    person_confidence: float = 0.0
    tracked_person_id: Optional[int] = None
    resident_id: str = "resident_eleanor_vance"
    current_activity: str = "IDLE"
    current_posture: PostureType = PostureType.UNKNOWN
    movement_rate: float = 0.0
    inactivity_duration_sec: float = 0.0
    zone_visit_duration_sec: float = 0.0
    expected_duration_sec: float = 600.0
    baseline_deviation: float = 0.0
    behavior_state: str = "NORMAL"
    fall_candidate: bool = False
    fall_confirmed: bool = False
    recovery_state: RecoveryStatus = RecoveryStatus.NONE
    last_seen_time: Optional[str] = None
    last_frame_timestamp: Optional[str] = None
    inference_fps: float = 0.0
    risk_level: SeverityLevel = SeverityLevel.LOW
