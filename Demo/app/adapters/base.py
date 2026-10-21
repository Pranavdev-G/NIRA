"""
Base Adapter Interfaces for External & Simulated Integrations.
Amazon Developer Hackathon 2026.

Clearly enforces Principle 5 & 7:
  - Explicitly tags every integration as:
    REAL, SIMULATED, MOCK, FUTURE.
  - Never claims real 911 dispatch or carrier SMS without authorized provider.
"""

from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class IntegrationType(str, Enum):
    REAL = "REAL"              # Connected to authenticated live provider
    SIMULATED = "SIMULATED"    # Local software simulation adapter
    MOCK = "MOCK"              # Synthetic unit test fixture
    FUTURE = "FUTURE"          # Planned future integration stub


class AdapterResult(BaseModel):
    """Standardized response envelope for all external and simulated adapters."""
    success: bool
    integration_type: str = IntegrationType.SIMULATED.value
    provider_name: str
    transaction_id: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "SIMULATION ADAPTER - Not connected to live external carrier/PSAP."
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseEmergencyCADAdapter(ABC):
    """Interface for Computer Aided Dispatch (CAD) 911 / EMS systems."""

    @abstractmethod
    async def dispatch_emergency(
        self,
        emergency_packet_id: str,
        triage_priority: str,
        cad_agency_code: str,
        location_address: str,
        formatted_summary: str,
        resident_name: str,
        medical_notes: List[str]
    ) -> AdapterResult:
        pass


class BaseSmartLockAdapter(ABC):
    """Interface for Smart Lock IoT hardware (August, Yale, Schlage, Matter)."""

    @abstractmethod
    async def unlock_door(
        self,
        device_id: str,
        actor: str,
        reason: str,
        temporary_pin: Optional[str] = None
    ) -> AdapterResult:
        pass

    @abstractmethod
    async def lock_door(
        self,
        device_id: str,
        actor: str,
        reason: str
    ) -> AdapterResult:
        pass


class BaseCaregiverMessagingAdapter(ABC):
    """Interface for multi-channel caregiver communication (SMS, Push, Alexa Drop-In)."""

    @abstractmethod
    async def send_message(
        self,
        recipient: str,
        headline: str,
        body: str,
        priority: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        pass
