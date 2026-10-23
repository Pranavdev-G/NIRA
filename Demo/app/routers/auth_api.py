"""
Demo Authentication & Session REST API for NIRA.
Amazon Developer Hackathon 2026.

Provides demo-local authentication:
- Role-aware authorization (Family Admin, Senior Home View, EMS Responder)
- Validates demo credentials and rejects invalid logins
- Issues persistent demo session tokens
- Exposes session inspection and clean logout
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field, EmailStr

router = APIRouter(prefix="/api/v1/auth", tags=["Demo Authentication & Sessions"])

# Authoritative Demo Accounts Database (In-Memory Demo Scope)
DEMO_ACCOUNTS = {
    "david.vance@example.com": {
        "password": "admin123",
        "name": "David Vance",
        "role": "admin",
        "title": "Family Admin & Guardian",
        "patient_id": "PT-84920",
        "permissions": ["admin_console", "live_telemetry", "door_override", "incident_resolve", "settings"],
        "default_redirect": "/admin"
    },
    "family@beaconhill.care": {
        "password": "family123",
        "name": "Eleanor Vance & Family",
        "role": "resident_family",
        "title": "Senior Monitored Home View",
        "patient_id": "PT-84920",
        "permissions": ["view_dashboard", "voice_assistant", "medications", "checkin", "video_reel"],
        "default_redirect": "/#demo/overview"
    },
    "medic14@bostonems.gov": {
        "password": "medic123",
        "name": "Medic 14 (Boston EMS)",
        "role": "ems_responder",
        "title": "First Responder CAD Terminal",
        "badge_id": "BEMS-8821",
        "patient_id": "PT-84920",
        "permissions": ["cad_dispatch", "smart_lock_unlock", "geofence_arrival", "emergency_packet"],
        "default_redirect": "/#demo/dispatch"
    }
}

# Active In-Memory Sessions: session_token -> user_data
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}


class LoginRequest(BaseModel):
    email: str = Field(..., description="Demo user email address")
    password: str = Field(..., description="Demo user password")
    role_hint: Optional[str] = Field(None, description="Optional 1-click role key")


class LoginResponse(BaseModel):
    success: bool
    session_token: str
    user: Dict[str, Any]
    redirect_url: str
    issued_at: str


@router.post("/login", response_model=LoginResponse, summary="Authenticate demo credentials")
async def login(req: LoginRequest):
    """
    Validates demo credentials against configured roles.
    Rejects invalid logins with 401 Unauthorized.
    """
    email_clean = req.email.strip().lower()
    user_info = DEMO_ACCOUNTS.get(email_clean)

    if not user_info or user_info["password"] != req.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please use the demo credentials guide."
        )

    # Issue deterministic session token
    token = f"demo-token-{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    session_record = {
        "session_token": token,
        "email": email_clean,
        "name": user_info["name"],
        "role": user_info["role"],
        "title": user_info["title"],
        "patient_id": user_info["patient_id"],
        "permissions": user_info["permissions"],
        "created_at": now_iso,
        "is_authenticated": True
    }
    ACTIVE_SESSIONS[token] = session_record

    return LoginResponse(
        success=True,
        session_token=token,
        user=session_record,
        redirect_url=user_info["default_redirect"],
        issued_at=now_iso
    )


@router.post("/logout", summary="Terminate active demo session")
async def logout(authorization: Optional[str] = Header(None)):
    """Terminates session token and clears authentication state."""
    token = None
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    return {"success": True, "message": "Demo session terminated cleanly."}


@router.get("/session", summary="Inspect current session info")
async def get_session(authorization: Optional[str] = Header(None)):
    """Validates session token and returns authenticated role details."""
    token = None
    if authorization:
        token = authorization.replace("Bearer ", "").strip()

    if not token or token not in ACTIVE_SESSIONS:
        # Fallback to default demo viewer if unauthenticated
        return {
            "is_authenticated": False,
            "role": "guest",
            "message": "Unauthenticated demo viewer. Use /login for role-aware access."
        }

    return {
        "is_authenticated": True,
        "session": ACTIVE_SESSIONS[token]
    }


@router.get("/roles", summary="List available demo profiles and credentials")
async def list_demo_roles():
    """Returns the list of available demo accounts for 1-click login."""
    return {
        "roles": [
            {
                "id": "admin_son",
                "email": "david.vance@example.com",
                "name": "David Vance (Son • Family Admin)",
                "role": "admin",
                "redirect": "/admin"
            },
            {
                "id": "senior_home",
                "email": "family@beaconhill.care",
                "name": "Eleanor & Family (Home View)",
                "role": "resident_family",
                "redirect": "/#demo/overview"
            },
            {
                "id": "ems",
                "email": "medic14@bostonems.gov",
                "name": "Medic 14 (Boston EMS Command)",
                "role": "ems_responder",
                "redirect": "/#demo/dispatch"
            }
        ]
    }
