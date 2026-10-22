"""
MongoDB Atlas Client, Collection Manager, and Real-Time Synchronization for NIRA.
Amazon Developer Hackathon 2026.

Integrates with MongoDB Atlas cluster:
mongodb+srv://dharaneesh0530_db_user:Dharaneesh!30@cluster0.hgkmalq.mongodb.net/
Database: nira_db
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

logger = logging.getLogger("NIRA.MongoDB")

# MongoDB Atlas configuration
DEFAULT_MONGO_URI = (
    "mongodb+srv://dharaneesh0530_db_user:Dharaneesh!30@cluster0.hgkmalq.mongodb.net/?retryWrites=true&w=majority"
)
MONGODB_URI = os.getenv("MONGODB_URI", DEFAULT_MONGO_URI)
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "nira_db")

# Singleton client reference
_mongo_client: Optional[Any] = None


def get_mongo_client() -> Optional[Any]:
    """Returns a singleton MongoClient configured with resilient timeouts and pooling."""
    global _mongo_client
    if not PYMONGO_AVAILABLE:
        logger.warning("pymongo is not installed; MongoDB features will be disabled.")
        return None

    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
                socketTimeoutMS=5000,
                maxPoolSize=50,
                appname="NIRA-AegisCare"
            )
            # Lightweight ping to verify connection
            _mongo_client.admin.command("ping")
            logger.info(f"[MongoDB] Connected successfully to cluster (db: {MONGODB_DB_NAME}).")
        except Exception as e:
            logger.warning(f"[MongoDB] Connection initialization warning: {e}")
            return None

    return _mongo_client


def get_mongo_db() -> Optional[Any]:
    """Returns the active MongoDB database instance."""
    client = get_mongo_client()
    if client is not None:
        return client[MONGODB_DB_NAME]
    return None


def serialize_for_mongo(obj: Any) -> Any:
    """Recursively serializes Python, SQLAlchemy, or Datetime objects into MongoDB-compatible dicts."""
    if obj is None:
        return None
    if isinstance(obj, (int, float, str, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, list):
        return [serialize_for_mongo(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): serialize_for_mongo(v) for k, v in obj.items()}
    # SQLAlchemy or Pydantic model
    if hasattr(obj, "model_dump"):
        return serialize_for_mongo(obj.model_dump())
    if hasattr(obj, "__dict__"):
        d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return serialize_for_mongo(d)
    return str(obj)


def init_mongo_db():
    """
    Initializes collections, creates performance indexes, and seeds the default senior profile.
    Safe to call repeatedly on startup.
    """
    db = get_mongo_db()
    if db is None:
        logger.warning("[MongoDB] Skipping initialization: database unavailable.")
        return

    try:
        # 1. Collection Indexes
        db.users.create_index([("id", ASCENDING)], unique=True)
        db.users.create_index([("patient_id", ASCENDING)], unique=True)

        db.incidents.create_index([("id", ASCENDING)], unique=True)
        db.incidents.create_index([("user_id", ASCENDING)])
        db.incidents.create_index([("status", ASCENDING)])
        db.incidents.create_index([("created_at", DESCENDING)])

        db.incident_timelines.create_index([("incident_id", ASCENDING)])
        db.incident_timelines.create_index([("timestamp", DESCENDING)])

        db.emergency_packets.create_index([("incident_id", ASCENDING)], unique=True)
        db.emergency_packets.create_index([("packet_id", ASCENDING)], unique=True)

        db.telemetry_events.create_index([("id", ASCENDING)], unique=True)
        db.telemetry_events.create_index([("correlation_id", ASCENDING)])
        db.telemetry_events.create_index([("resident_id", ASCENDING)])
        db.telemetry_events.create_index([("timestamp", DESCENDING)])

        db.live_voice_interactions.create_index([("id", ASCENDING)], unique=True)
        db.live_voice_interactions.create_index([("elderly_id", ASCENDING)])
        db.live_voice_interactions.create_index([("timestamp", DESCENDING)])

        # 2. Seed default senior profile if missing
        default_user = {
            "id": "user_eleanor_vance",
            "patient_id": "PT-84920",
            "name": "Eleanor Vance",
            "age": 79,
            "residence_address": "Residence Unit 4B - Beacon Hill, Boston MA",
            "emergency_contact": "Sarah Vance (Daughter) - +1-555-019-2834",
            "dnr_order": False,
            "medical_history": [
                "Mild cognitive impairment (early stage)",
                "Hypertension (managed with Lisinopril)",
                "Documented history of slip & fall in bathroom (Jan 2026)",
                "Penicillin allergy (Anaphylaxis risk)"
            ],
            "baseline_parameters": {
                "resting_heart_rate_bpm": 72,
                "average_sleep_start_hour": 23,
                "average_wake_hour": 7,
                "normal_gait_velocity_mps": 0.95
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        db.users.update_one({"id": "user_eleanor_vance"}, {"$setOnInsert": default_user}, upsert=True)
        logger.info("[MongoDB] Default user profile verified/seeded in MongoDB users collection.")

    except Exception as e:
        logger.warning(f"[MongoDB] Index creation or seeding warning: {e}")


def sync_model_to_mongo(instance: Any) -> bool:
    """
    Asynchronously or synchronously synchronizes any SQLAlchemy model instance into MongoDB.
    Uses upsert by primary identifier.
    """
    db = get_mongo_db()
    if db is None:
        return False

    try:
        table_name = getattr(instance, "__tablename__", None)
        if not table_name:
            return False

        doc = serialize_for_mongo(instance)
        if not doc:
            return False

        if table_name == "users":
            db.users.replace_one({"id": doc.get("id")}, doc, upsert=True)
        elif table_name == "incidents":
            db.incidents.replace_one({"id": doc.get("id")}, doc, upsert=True)
        elif table_name == "incident_timelines":
            if doc.get("id"):
                db.incident_timelines.replace_one({"id": doc["id"]}, doc, upsert=True)
            else:
                db.incident_timelines.replace_one(
                    {
                        "incident_id": doc.get("incident_id"),
                        "timestamp": doc.get("timestamp"),
                        "action_type": doc.get("action_type")
                    },
                    doc,
                    upsert=True
                )
        elif table_name == "emergency_packets":
            db.emergency_packets.replace_one({"incident_id": doc.get("incident_id")}, doc, upsert=True)
        elif table_name == "telemetry_events":
            db.telemetry_events.replace_one({"id": doc.get("id")}, doc, upsert=True)
        elif table_name == "live_voice_interactions":
            db.live_voice_interactions.replace_one({"id": doc.get("id")}, doc, upsert=True)
        else:
            return False

        return True
    except Exception as e:
        logger.debug(f"[MongoDB] Sync error for {getattr(instance, '__tablename__', 'unknown')}: {e}")
        return False


def check_mongo_health() -> Dict[str, Any]:
    """Pings the cluster and returns comprehensive health and collection statistics."""
    start = time.perf_counter()
    db = get_mongo_db()
    if db is None:
        return {
            "status": "disconnected",
            "error": "MongoClient not available or connection timed out",
            "cluster": "cluster0.hgkmalq.mongodb.net",
            "database": MONGODB_DB_NAME
        }

    try:
        client = get_mongo_client()
        ping_res = client.admin.command("ping")
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)

        collections = db.list_collection_names()
        counts = {}
        for coll in ["users", "incidents", "incident_timelines", "emergency_packets", "telemetry_events", "live_voice_interactions"]:
            if coll in collections:
                counts[coll] = db[coll].count_documents({})
            else:
                counts[coll] = 0

        return {
            "status": "connected",
            "cluster": "cluster0.hgkmalq.mongodb.net",
            "database": MONGODB_DB_NAME,
            "ping_ms": latency_ms,
            "ping_result": ping_res,
            "collections_count": len(collections),
            "document_counts": counts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "cluster": "cluster0.hgkmalq.mongodb.net",
            "database": MONGODB_DB_NAME
        }
