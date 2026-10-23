"""
Database Storage and Telemetry Logging for NIRA Live Voice Interactions.
Amazon Developer Hackathon 2026.

Supports hybrid persistence:
  1. Primary: MongoDB Atlas cluster (cluster0.hgkmalq.mongodb.net, database: nira_db)
  2. Local Fallback/Mirror: aegis_care.db SQLite
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from .models import VoiceInteractionResult

try:
    from pymongo import MongoClient, DESCENDING
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

logger = logging.getLogger("NIRA.VoiceStorage")

DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "aegis_care.db"))
DEFAULT_MONGO_URI = (
    "mongodb+srv://dharaneesh0530_db_user:Dharaneesh!30@cluster0.hgkmalq.mongodb.net/?retryWrites=true&w=majority"
)
MONGODB_URI = os.getenv("MONGODB_URI", DEFAULT_MONGO_URI)
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "nira_db")


class VoiceStorage:
    """
    Manages persistent logging of live speech check-in interactions.
    Persists to MongoDB Atlas in real time, with local SQLite mirror.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH, mongo_uri: Optional[str] = None):
        self.db_path = db_path
        self.mongo_uri = mongo_uri or MONGODB_URI
        self._mongo_client = None
        self._init_mongo()
        self._init_tables()

    def _init_mongo(self):
        """Initializes MongoDB Atlas connection if pymongo is installed."""
        if not PYMONGO_AVAILABLE:
            return
        try:
            self._mongo_client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
                socketTimeoutMS=5000,
                maxPoolSize=20,
                appname="NIRA-LiveVoice"
            )
            # Lightweight ping
            self._mongo_client.admin.command("ping")
            logger.info("[VoiceStorage] Connected to MongoDB Atlas cluster.")
        except Exception as e:
            logger.warning(f"[VoiceStorage] MongoDB initialization notice: {e}")
            self._mongo_client = None

    def _get_mongo_db(self):
        if self._mongo_client is not None:
            return self._mongo_client[MONGODB_DB_NAME]
        return None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Ensures the live_voice_interactions table exists alongside telemetry_events in SQLite."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS live_voice_interactions (
            id VARCHAR(64) PRIMARY KEY,
            elderly_id VARCHAR(64) NOT NULL,
            question VARCHAR(256) NOT NULL,
            transcript TEXT NOT NULL,
            language VARCHAR(16) NOT NULL,
            translated_transcript TEXT,
            status VARCHAR(32) NOT NULL,
            urgency VARCHAR(32) NOT NULL,
            reason TEXT NOT NULL,
            action VARCHAR(64) NOT NULL,
            model VARCHAR(64) NOT NULL,
            transcription_quality VARCHAR(32),
            duration_sec FLOAT DEFAULT 0.0,
            processing_time_sec FLOAT DEFAULT 0.0,
            timestamp VARCHAR(64) NOT NULL,
            metadata_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_voice_elderly ON live_voice_interactions(elderly_id);
        CREATE INDEX IF NOT EXISTS idx_voice_status ON live_voice_interactions(status);
        CREATE INDEX IF NOT EXISTS idx_voice_timestamp ON live_voice_interactions(timestamp);
        """
        try:
            with self._get_connection() as conn:
                conn.executescript(create_sql)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize voice interaction SQLite tables: {e}")

    def log_interaction(self, result: VoiceInteractionResult, room_id: str = "living_room") -> bool:
        """
        Persists voice check-in result to both MongoDB Atlas and SQLite:
          1. live_voice_interactions (detailed speech record)
          2. telemetry_events (authoritative NIRA multimodal event stream)
        """
        now_dt = datetime.now(timezone.utc)
        meta_dict = result.metadata or {}

        voice_doc = {
            "id": result.interaction_id,
            "elderly_id": result.elderly_id,
            "question": result.question,
            "transcript": result.transcript,
            "language": result.language,
            "translated_transcript": result.translated_transcript,
            "status": str(result.status.value),
            "urgency": str(result.urgency.value),
            "reason": result.reason,
            "action": str(result.action.value),
            "model": result.model,
            "transcription_quality": result.transcription_quality,
            "duration_sec": result.duration_sec,
            "processing_time_sec": result.processing_time_sec,
            "timestamp": result.timestamp,
            "metadata_json": meta_dict
        }

        telemetry_payload = {
            "interaction_id": result.interaction_id,
            "question": result.question,
            "transcript": result.transcript,
            "language": result.language,
            "translated_transcript": result.translated_transcript,
            "status": str(result.status.value),
            "urgency": str(result.urgency.value),
            "reason": result.reason,
            "action": str(result.action.value),
            "model": result.model,
            "transcription_quality": result.transcription_quality,
            "duration_sec": result.duration_sec,
            "processing_time_sec": result.processing_time_sec
        }

        telemetry_doc = {
            "id": f"evt-vox-{result.interaction_id}",
            "correlation_id": f"corr-{result.interaction_id}",
            "resident_id": result.elderly_id,
            "room_id": room_id,
            "source": "live_whisper_voice",
            "event_type": f"voice_check_in_{result.status.value.lower()}",
            "confidence": 1.0,
            "payload_json": telemetry_payload,
            "timestamp": now_dt.isoformat(),
            "created_at": now_dt.isoformat(),
            "safety_state_after": result.status.value,
            "evidence_summary": [result.reason]
        }

        # 1. Primary write to MongoDB Atlas
        mongo_saved = False
        try:
            mongo_db = self._get_mongo_db()
            if mongo_db is not None:
                mongo_db.live_voice_interactions.replace_one({"id": result.interaction_id}, voice_doc, upsert=True)
                mongo_db.telemetry_events.replace_one({"id": telemetry_doc["id"]}, telemetry_doc, upsert=True)
                mongo_saved = True
                logger.info(f"[VoiceStorage] Saved voice interaction {result.interaction_id} to MongoDB Atlas.")
        except Exception as me:
            logger.warning(f"[VoiceStorage] MongoDB persistence notice: {me}")

        # 2. Local SQLite write
        sqlite_saved = False
        meta_str = json.dumps(meta_dict)
        insert_voice_sql = """
        INSERT OR REPLACE INTO live_voice_interactions (
            id, elderly_id, question, transcript, language, translated_transcript,
            status, urgency, reason, action, model, transcription_quality,
            duration_sec, processing_time_sec, timestamp, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        insert_telemetry_sql = """
        INSERT OR REPLACE INTO telemetry_events (
            id, correlation_id, resident_id, room_id, source, event_type,
            confidence, payload_json, timestamp, created_at, safety_state_after, evidence_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(insert_voice_sql, (
                    result.interaction_id,
                    result.elderly_id,
                    result.question,
                    result.transcript,
                    result.language,
                    result.translated_transcript,
                    str(result.status.value),
                    str(result.urgency.value),
                    result.reason,
                    str(result.action.value),
                    result.model,
                    result.transcription_quality,
                    result.duration_sec,
                    result.processing_time_sec,
                    result.timestamp,
                    meta_str
                ))

                # Check if telemetry_events table exists
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='telemetry_events';")
                if cur.fetchone():
                    cur.execute(insert_telemetry_sql, (
                        telemetry_doc["id"],
                        telemetry_doc["correlation_id"],
                        telemetry_doc["resident_id"],
                        telemetry_doc["room_id"],
                        telemetry_doc["source"],
                        telemetry_doc["event_type"],
                        1.0,
                        json.dumps(telemetry_payload),
                        now_dt.isoformat(),
                        now_dt.isoformat(),
                        result.status.value,
                        json.dumps([result.reason])
                    ))

                conn.commit()
                sqlite_saved = True
        except Exception as e:
            logger.error(f"Error persisting voice interaction {result.interaction_id} to SQLite: {e}")

        return mongo_saved or sqlite_saved

    def get_recent_interactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent voice interactions from MongoDB Atlas (falling back to SQLite)."""
        # Try MongoDB Atlas first
        try:
            mongo_db = self._get_mongo_db()
            if mongo_db is not None:
                cursor = mongo_db.live_voice_interactions.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
                docs = list(cursor)
                if docs:
                    return docs
        except Exception as me:
            logger.warning(f"[VoiceStorage] Could not query MongoDB; falling back to SQLite: {me}")

        # SQLite fallback
        sql = """
        SELECT * FROM live_voice_interactions
        ORDER BY timestamp DESC
        LIMIT ?;
        """
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    if item.get("metadata_json"):
                        try:
                            item["metadata"] = json.loads(item["metadata_json"])
                        except Exception:
                            item["metadata"] = {}
                    results.append(item)
                return results
        except Exception as e:
            logger.error(f"Error reading voice interactions from SQLite: {e}")
            return []
