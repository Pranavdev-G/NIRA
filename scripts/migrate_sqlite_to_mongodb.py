"""
Migrates existing SQLite records from aegis_care.db into MongoDB Atlas (nira_db)
using high-performance bulk operations.
Amazon Developer Hackathon 2026.
"""

import os
import sys
import json
import sqlite3
from pymongo import ReplaceOne

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMO_DIR = os.path.join(ROOT_DIR, "Demo")
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)

from app.database.mongo import get_mongo_db, init_mongo_db


def migrate():
    print("[NIRA Migration] Initializing connection to MongoDB Atlas...")
    db_path = os.path.join(ROOT_DIR, "aegis_care.db")
    if not os.path.exists(db_path):
        print(f"No sqlite database found at {db_path}")
        return

    init_mongo_db()
    mongo_db = get_mongo_db()
    if mongo_db is None:
        print("MongoDB connection failed; aborting migration.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Users
    try:
        cur.execute("SELECT * FROM users")
        users = [dict(row) for row in cur.fetchall()]
        if users:
            ops = []
            for u in users:
                for json_col in ["medical_history", "baseline_parameters"]:
                    if u.get(json_col) and isinstance(u[json_col], str):
                        try:
                            u[json_col] = json.loads(u[json_col])
                        except Exception:
                            pass
                ops.append(ReplaceOne({"id": u["id"]}, u, upsert=True))
            mongo_db.users.bulk_write(ops)
        print(f"[Users] Migrated {len(users)} users.")
    except Exception as e:
        print(f"[Users] Migration error: {e}")

    # 2. Incidents
    try:
        cur.execute("SELECT * FROM incidents")
        incidents = [dict(row) for row in cur.fetchall()]
        if incidents:
            ops = []
            for inc in incidents:
                for json_col in ["risk_reasons", "context_snapshot"]:
                    if inc.get(json_col) and isinstance(inc[json_col], str):
                        try:
                            inc[json_col] = json.loads(inc[json_col])
                        except Exception:
                            pass
                ops.append(ReplaceOne({"id": inc["id"]}, inc, upsert=True))
            mongo_db.incidents.bulk_write(ops)
        print(f"[Incidents] Migrated {len(incidents)} incidents.")
    except Exception as e:
        print(f"[Incidents] Migration error: {e}")

    # 3. Incident Timelines
    try:
        cur.execute("SELECT * FROM incident_timelines")
        timelines = [dict(row) for row in cur.fetchall()]
        if timelines:
            # Batch in chunks of 500
            chunk_size = 500
            for i in range(0, len(timelines), chunk_size):
                chunk = timelines[i:i + chunk_size]
                ops = []
                for t in chunk:
                    for json_col in ["evidence", "metadata_json"]:
                        if t.get(json_col) and isinstance(t[json_col], str):
                            try:
                                t[json_col] = json.loads(t[json_col])
                            except Exception:
                                pass
                    ops.append(ReplaceOne({"id": t["id"]}, t, upsert=True))
                mongo_db.incident_timelines.bulk_write(ops)
        print(f"[Incident Timelines] Migrated {len(timelines)} timelines.")
    except Exception as e:
        print(f"[Incident Timelines] Migration error: {e}")

    # 4. Emergency Packets
    try:
        cur.execute("SELECT * FROM emergency_packets")
        packets = [dict(row) for row in cur.fetchall()]
        if packets:
            ops = []
            for p in packets:
                if p.get("packet_json") and isinstance(p["packet_json"], str):
                    try:
                        p["packet_json"] = json.loads(p["packet_json"])
                    except Exception:
                        pass
                ops.append(ReplaceOne({"incident_id": p["incident_id"]}, p, upsert=True))
            mongo_db.emergency_packets.bulk_write(ops)
        print(f"[Emergency Packets] Migrated {len(packets)} emergency packets.")
    except Exception as e:
        print(f"[Emergency Packets] Migration error: {e}")

    # 5. Telemetry Events
    try:
        cur.execute("SELECT * FROM telemetry_events")
        telemetry = [dict(row) for row in cur.fetchall()]
        if telemetry:
            chunk_size = 500
            for i in range(0, len(telemetry), chunk_size):
                chunk = telemetry[i:i + chunk_size]
                ops = []
                for te in chunk:
                    for json_col in ["payload_json", "evidence_summary"]:
                        if te.get(json_col) and isinstance(te[json_col], str):
                            try:
                                te[json_col] = json.loads(te[json_col])
                            except Exception:
                                pass
                    ops.append(ReplaceOne({"id": te["id"]}, te, upsert=True))
                mongo_db.telemetry_events.bulk_write(ops)
        print(f"[Telemetry Events] Migrated {len(telemetry)} telemetry events.")
    except Exception as e:
        print(f"[Telemetry Events] Migration error: {e}")

    # 6. Live Voice Interactions
    try:
        cur.execute("SELECT * FROM live_voice_interactions")
        voice_records = [dict(row) for row in cur.fetchall()]
        if voice_records:
            ops = []
            for vr in voice_records:
                if vr.get("metadata_json") and isinstance(vr["metadata_json"], str):
                    try:
                        vr["metadata_json"] = json.loads(vr["metadata_json"])
                    except Exception:
                        pass
                ops.append(ReplaceOne({"id": vr["id"]}, vr, upsert=True))
            mongo_db.live_voice_interactions.bulk_write(ops)
        print(f"[Live Voice Interactions] Migrated {len(voice_records)} voice records.")
    except Exception as e:
        print(f"[Live Voice Interactions] Migration error: {e}")

    conn.close()
    print("Migration from SQLite to MongoDB Atlas completed successfully.")


if __name__ == "__main__":
    migrate()
