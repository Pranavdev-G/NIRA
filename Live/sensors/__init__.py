"""
Live Sensor Adapters Package for NIRA.
Amazon Developer Hackathon 2026.

Normalized sensor ingestion layer strictly distinguishing physical hardware from simulation.
"""

from .base import (
    SensorSourceType,
    ConnectionState,
    SensorReading,
    BaseSensorAdapter
)
from .wearable import (
    WearableReading,
    BaseWearableAdapter,
    RealWearableAdapter,
    SimulatedWearableAdapter
)
from .radar import (
    RadarReading,
    BaseRadarAdapter,
    RealRadarAdapter,
    SimulatedRadarAdapter
)
from .environment import (
    EnvironmentReading,
    BaseEnvironmentAdapter,
    RealEnvironmentAdapter,
    SimulatedEnvironmentAdapter
)
from .gps import (
    GPSReading,
    BaseGPSAdapter,
    RealGPSAdapter,
    SimulatedGPSAdapter
)

__all__ = [
    "SensorSourceType",
    "ConnectionState",
    "SensorReading",
    "BaseSensorAdapter",
    "WearableReading",
    "BaseWearableAdapter",
    "RealWearableAdapter",
    "SimulatedWearableAdapter",
    "RadarReading",
    "BaseRadarAdapter",
    "RealRadarAdapter",
    "SimulatedRadarAdapter",
    "EnvironmentReading",
    "BaseEnvironmentAdapter",
    "RealEnvironmentAdapter",
    "SimulatedEnvironmentAdapter",
    "GPSReading",
    "BaseGPSAdapter",
    "RealGPSAdapter",
    "SimulatedGPSAdapter"
]
