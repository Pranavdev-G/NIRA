"""
MongoDB Atlas Direct Data Access & Telemetry REST API.
Amazon Developer Hackathon 2026.

Exposes endpoints under /api/v1/mongo:
  - GET  /status: Reports MongoDB Atlas connectivity, latency, and collection stats
  - GET  /users: Returns resident profile directly from MongoDB
  - GET  /incidents: Queries incidents collection with optional status filter
  - GET  /incidents/{incident_id}/timeline: Returns chronological audit trail from MongoDB
  - GET  /telemetry: Returns telemetry events collection
  - GET  /voice-interactions: Returns voice records collection
  - POST /sync: Synchronizes all local SQLite records to MongoDB Atlas
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from app.database.mongo import get_mongo_db, check_mongo_health

router = APIRouter(prefix="/api/v1/mongo", tags=["MongoDB Atlas Cloud Database"])


@router.get("/status", summary="Get MongoDB Atlas cluster connection status and metrics")
def get_status() -> Dict[str, Any]:
    """Returns real-time MongoDB cluster connectivity, latency, and collection document counts."""
    return check_mongo_health()


@router.get("/users", summary="Get resident profiles from MongoDB")
def get_users() -> List[Dict[str, Any]]:
    """Returns resident profile documents from MongoDB Atlas."""
    db = get_mongo_db()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB Atlas unavailable")
    return list(db.users.find({}, {"_id": 0}))


@router.get("/incidents", summary="Query incidents directly from MongoDB Atlas")
def get_incidents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ACTIVE, RESOLVED, etc.)"),
    limit: int = Query(50, ge=1, le=500)
) -> List[Dict[str, Any]]:
    """Retrieves incidents stored in MongoDB Atlas."""
    db = get_mongo_db()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB Atlas unavailable")

    query = {}
    if status_filter:
        query["status"] = status_filter

    cursor = db.incidents.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return list(cursor)


@router.get("/incidents/{incident_id}/timeline", summary="Get incident timeline from MongoDB")
def get_incident_timeline(incident_id: str) -> List[Dict[str, Any]]:
    """Retrieves the chronological audit log for a specific incident from MongoDB Atlas."""
    db = get_mongo_db()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB Atlas unavailable")

    cursor = db.incident_timelines.find({"incident_id": incident_id}, {"_id": 0}).sort("timestamp", 1)
    return list(cursor)


@router.get("/telemetry", summary="Query telemetry stream directly from MongoDB Atlas")
def get_telemetry(
    limit: int = Query(50, ge=1, le=500),
    source: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves sensor and vision telemetry records from MongoDB Atlas."""
    db = get_mongo_db()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB Atlas unavailable")

    query = {}
    if source:
        query["source"] = source

    cursor = db.telemetry_events.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return list(cursor)


@router.get("/voice-interactions", summary="Query live voice interactions directly from MongoDB Atlas")
def get_voice_interactions(limit: int = Query(50, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Retrieves Whisper voice check-in interactions stored in MongoDB Atlas."""
    db = get_mongo_db()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB Atlas unavailable")

    cursor = db.live_voice_interactions.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return list(cursor)


@router.post("/sync", summary="Synchronize SQLite records to MongoDB Atlas")
def trigger_sync() -> Dict[str, Any]:
    """Manually triggers bulk sync from local SQLite database into MongoDB Atlas."""
    import importlib.util
    import os
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    script_path = os.path.join(root_dir, "scripts", "migrate_sqlite_to_mongodb.py")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="Migration script not found")

    spec = importlib.util.spec_from_file_location("migrator", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate()

    health = check_mongo_health()
    return {"status": "SUCCESS", "message": "Synced to MongoDB Atlas", "metrics": health}
