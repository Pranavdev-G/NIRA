"""
MongoDB Atlas Database Connector for Live NIRA System.
Amazon Developer Hackathon 2026.
"""

import logging
from typing import Optional, Any
from pymongo import MongoClient
from pymongo.database import Database
from Live.app.config import settings

logger = logging.getLogger("NIRA.LiveDB")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_mongo_db() -> Optional[Database]:
    """Returns singleton MongoDB Atlas database instance for Live system."""
    global _client, _db
    if _db is not None:
        return _db

    try:
        uri = settings.MONGODB_URI
        db_name = settings.MONGODB_DB_NAME
        logger.info(f"[LiveDB] Connecting to MongoDB Atlas cluster at: {uri.split('@')[-1]}")
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
        _client.admin.command("ping")
        _db = _client[db_name]
        logger.info(f"[LiveDB] Connected successfully to MongoDB Atlas database: {db_name}")

        # Ensure indexes
        try:
            _db.caregivers.create_index("email", unique=True, sparse=True)
            _db.caregivers.create_index("mobile_number")
            _db.reminders.create_index("time_slot")
            _db.telemetry.create_index("timestamp")
        except Exception as ie:
            logger.debug(f"[LiveDB] Index notice: {ie}")

        return _db
    except Exception as e:
        logger.warning(f"[LiveDB] MongoDB Atlas connection warning: {e}. Running in memory fallback.")
        return None
