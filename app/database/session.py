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
