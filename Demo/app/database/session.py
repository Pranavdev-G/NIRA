"""
Database Engine, Session Management, and Automatic Seeding.
Amazon Developer Hackathon 2026.
Supports SQLite (default local) and PostgreSQL (via DATABASE_URL).
"""

import os
from datetime import datetime, timezone
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.models import Base, UserModel
from app.config import settings

# Database connection URL - default to lightweight local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegis_care.db")

# SQLite connection args for multi-threaded FastAPI concurrency
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for thread-safe database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes tables and seeds default senior profile (Eleanor Vance)."""
    Base.metadata.create_all(bind=engine)

    # Safe lightweight SQLite column migration if tables pre-existed
    if DATABASE_URL.startswith("sqlite"):
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(incidents);")).fetchall()
                existing_cols = {row[1] for row in res}
                if existing_cols:
                    if "workflow_state" not in existing_cols:
                        conn.execute(text("ALTER TABLE incidents ADD COLUMN workflow_state VARCHAR(64) DEFAULT 'DETECTED';"))
                    if "correlation_id" not in existing_cols:
                        conn.execute(text("ALTER TABLE incidents ADD COLUMN correlation_id VARCHAR(64);"))
                    if "idempotency_key" not in existing_cols:
                        conn.execute(text("ALTER TABLE incidents ADD COLUMN idempotency_key VARCHAR(128);"))

                res_t = conn.execute(text("PRAGMA table_info(incident_timelines);")).fetchall()
                existing_t_cols = {row[1] for row in res_t}
                if existing_t_cols:
                    if "previous_state" not in existing_t_cols:
                        conn.execute(text("ALTER TABLE incident_timelines ADD COLUMN previous_state VARCHAR(64);"))
                    if "new_state" not in existing_t_cols:
                        conn.execute(text("ALTER TABLE incident_timelines ADD COLUMN new_state VARCHAR(64);"))
                    if "reason" not in existing_t_cols:
                        conn.execute(text("ALTER TABLE incident_timelines ADD COLUMN reason TEXT;"))
                    if "evidence" not in existing_t_cols:
                        conn.execute(text("ALTER TABLE incident_timelines ADD COLUMN evidence JSON;"))
                    if "correlation_id" not in existing_t_cols:
                        conn.execute(text("ALTER TABLE incident_timelines ADD COLUMN correlation_id VARCHAR(64);"))
                conn.commit()
        except Exception:
            pass

    # Seed default user profile if absent
    with SessionLocal() as db:
        user = db.query(UserModel).filter(UserModel.id == "user_eleanor_vance").first()
        if not user:
            default_user = UserModel(
                id="user_eleanor_vance",
                patient_id=settings.DEFAULT_PATIENT_ID,
                name=settings.DEFAULT_PATIENT_NAME,
                age=79,
                residence_address=settings.DEFAULT_LOCATION_LABEL,
                emergency_contact=f"{settings.PRIMARY_CAREGIVER_NAME} ({settings.PRIMARY_CAREGIVER_PHONE})",
                dnr_order=False,
                medical_history=[
                    "Mild cognitive impairment (early stage)",
                    "Hypertension (managed with Lisinopril)",
                    "Documented history of slip & fall in bathroom (Jan 2026)",
                    "Penicillin allergy (Anaphylaxis risk)"
                ],
                baseline_parameters={
                    "resting_heart_rate_bpm": 72,
                    "average_sleep_start_hour": 23,
                    "average_wake_hour": 7,
                    "normal_gait_velocity_mps": 0.95
                },
                created_at=datetime.now(timezone.utc)
            )
            db.add(default_user)
            db.commit()
