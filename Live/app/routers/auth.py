"""
Live Caretaker Authentication & Registration Router.
Amazon Developer Hackathon 2026.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from Live.app.database import get_mongo_db
from Live.app.services.session import LiveSessionManager

router = APIRouter(prefix="/api/v1/live/auth", tags=["Live Caregiver Authentication"])


class RegisterPayload(BaseModel):
    caretaker_name: str = Field(..., description="Caretaker full name")
    mobile_number: str = Field(..., description="Caretaker mobile number")
    email: str = Field(..., description="Caretaker email")
    caring_person_name: str = Field(..., description="Senior/Patient name")
    address: str = Field(..., description="Residence street address")
    latitude: Optional[float] = Field(None, description="GPS latitude")
    longitude: Optional[float] = Field(None, description="GPS longitude")
    maps_link: Optional[str] = Field(None, description="Live Google Maps link")
    age: int = Field(79, description="Senior age")
    disabilities: Optional[str] = Field("None noted", description="Disabilities")
    health_issues: Optional[str] = Field("None noted", description="Health issues")
    password: str = Field(..., min_length=4, description="Password")


class LoginPayload(BaseModel):
    identifier: str = Field(..., description="Username, mobile number, or email")
    password: str = Field(..., description="Password")


@router.post("/register", summary="Register caretaker and senior profile")
def register_caretaker(payload: RegisterPayload):
    mongo_db = get_mongo_db()
    data = payload.dict()
    doc = LiveSessionManager.register(data, mongo_db=mongo_db)
    return {
        "success": True,
        "message": "Caretaker and senior profile registered successfully.",
        "token": f"live_tok_{doc['id']}",
        "caregiver": {
            "id": doc["id"],
            "name": doc["caretaker_name"],
            "mobile": doc["mobile_number"],
            "email": doc["email"],
            "username": doc["username"]
        },
        "patient": LiveSessionManager.get_active_patient_info()
    }


@router.post("/login", summary="Sign in via username, mobile, or email")
def login_caretaker(payload: LoginPayload):
    mongo_db = get_mongo_db()
    user = LiveSessionManager.authenticate(
        identifier=payload.identifier,
        password=payload.password,
        mongo_db=mongo_db
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your username, mobile number, or password."
        )

    return {
        "success": True,
        "message": "Sign-in successful. Live session active.",
        "token": f"live_tok_{user.get('id', 'default')}",
        "caregiver": {
            "id": user.get("id"),
            "name": user.get("caretaker_name"),
            "mobile": user.get("mobile_number"),
            "email": user.get("email"),
            "username": user.get("username")
        },
        "patient": LiveSessionManager.get_active_patient_info()
    }


@router.get("/session", summary="Get active caretaker and senior profile")
def get_session():
    return {
        "authenticated": True,
        "caregiver": LiveSessionManager.get_active_caregiver(),
        "patient": LiveSessionManager.get_active_patient_info()
    }


@router.post("/logout", summary="Log out active session")
def logout():
    LiveSessionManager.set_active_caregiver(LiveSessionManager.get_active_caregiver())
    return {"success": True, "message": "Logged out successfully."}
