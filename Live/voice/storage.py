"""
Database Storage and Telemetry Logging for NIRA Live Voice Interactions.
Amazon Developer Hackathon 2026.

Reuses existing aegis_care.db schema (telemetry_events) while maintaining a dedicated
live_voice_interactions audit table for structured speech records.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from .models import VoiceInteractionResult

logger = logging.getLogger("NIRA.VoiceStorage")

DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "aegis_care.db"))


class VoiceStorage:
    """
    Manages persistent logging of live speech check-in interactions.
    Safe against schema alterations and thread concurrency.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Ensures the live_voice_interactions table exists alongside telemetry_events."""
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
            logger.error(f"Failed to initialize voice interaction tables: {e}")

    def log_interaction(self, result: VoiceInteractionResult, room_id: str = "living_room") -> bool:
        """
        Persists voice check-in result to both:
          1. live_voice_interactions (detailed speech record)
          2. telemetry_events (authoritative NIRA multimodal event stream)
        """
        now_dt = datetime.now(timezone.utc)
        meta_str = json.dumps(result.metadata)

        # 1. Insert into dedicated voice table
        insert_voice_sql = """
        INSERT OR REPLACE INTO live_voice_interactions (
            id, elderly_id, question, transcript, language, translated_transcript,
            status, urgency, reason, action, model, transcription_quality,
            duration_sec, processing_time_sec, timestamp, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        # 2. Insert into unified telemetry_events table
        insert_telemetry_sql = """
        INSERT OR REPLACE INTO telemetry_events (
            id, correlation_id, resident_id, room_id, source, event_type,
            confidence, payload_json, timestamp, created_at, safety_state_after, evidence_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

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
                        f"evt-vox-{result.interaction_id}",
                        f"corr-{result.interaction_id}",
                        result.elderly_id,
                        room_id,
                        "live_whisper_voice",
                        f"voice_check_in_{result.status.value.lower()}",
                        1.0,
                        json.dumps(telemetry_payload),
                        now_dt.isoformat(),
                        now_dt.isoformat(),
                        result.status.value,
                        json.dumps([result.reason])
                    ))

                conn.commit()
                logger.info(f"Logged voice interaction {result.interaction_id} [{result.status.value}] to database.")
                return True
        except Exception as e:
            logger.error(f"Error persisting voice interaction {result.interaction_id}: {e}")
            return False

    def get_recent_interactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent voice interactions from audit table."""
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
            logger.error(f"Error reading voice interactions: {e}")
            return []
