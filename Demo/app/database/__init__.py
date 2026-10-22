"""Database package with hybrid SQLite & MongoDB Atlas support."""
from app.database.models import (
    Base, UserModel, IncidentModel,
    IncidentTimelineModel, EmergencyPacketModel, TelemetryEventModel
)
from app.database.session import engine, SessionLocal, get_db, init_db
from app.database.mongo import (
    get_mongo_client, get_mongo_db, init_mongo_db,
    sync_model_to_mongo, check_mongo_health
)

__all__ = [
    "Base",
    "UserModel",
    "IncidentModel",
    "IncidentTimelineModel",
    "EmergencyPacketModel",
    "TelemetryEventModel",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "get_mongo_client",
    "get_mongo_db",
    "init_mongo_db",
    "sync_model_to_mongo",
    "check_mongo_health"
]
