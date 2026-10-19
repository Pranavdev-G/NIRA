"""
NIRA External and Simulated Adapter Layer.
Amazon Developer Hackathon 2026.
"""

from app.adapters.base import (
    BaseEmergencyCADAdapter,
    BaseSmartLockAdapter,
    BaseCaregiverMessagingAdapter,
    AdapterResult,
    IntegrationType
)
from app.adapters.simulated_adapters import (
    SimulatedCADAdapter,
    SimulatedSmartLockAdapter,
    SimulatedSMSAdapter,
    SimulatedPushAdapter,
    SimulatedAlexaDropInAdapter,
    default_cad_adapter,
    default_lock_adapter,
    default_sms_adapter,
    default_push_adapter,
    default_alexa_adapter
)

__all__ = [
    "BaseEmergencyCADAdapter",
    "BaseSmartLockAdapter",
    "BaseCaregiverMessagingAdapter",
    "AdapterResult",
    "IntegrationType",
    "SimulatedCADAdapter",
    "SimulatedSmartLockAdapter",
    "SimulatedSMSAdapter",
    "SimulatedPushAdapter",
    "SimulatedAlexaDropInAdapter",
    "default_cad_adapter",
    "default_lock_adapter",
    "default_sms_adapter",
    "default_push_adapter",
    "default_alexa_adapter"
]
