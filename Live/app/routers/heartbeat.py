"""
Live Continuous Wearable Heartbeat & Device Telemetry Router.
Amazon Developer Hackathon 2026.
"""

from fastapi import APIRouter, Query
from Live.app.services.heartbeat import LiveHeartbeatService

router = APIRouter(prefix="/api/v1/live/heartbeat", tags=["Live Heartbeat & Wearable Monitoring"])


@router.get("/live", summary="Get continuous heartbeat and pulse telemetry")
def get_live_heartbeat(emergency: bool = Query(False, description="Simulate elevated emergency tachycardia")):
    return LiveHeartbeatService.get_live_heartbeat(is_emergency=emergency)


@router.get("/wearable", summary="Get wearable hardware device specifications")
def get_wearable_device():
    return {
        "success": True,
        "wearable": LiveHeartbeatService.get_wearable_device()
    }
