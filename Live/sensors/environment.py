"""
Environmental Sensor Adapter for NIRA Live.
Amazon Developer Hackathon 2026.

Collects ambient physical telemetry: temperature, humidity, ambient lux,
noise levels (dB), and floor moisture / wet-floor state.
Produces normalized evidence events without performing final safety risk scoring.
"""

import time
import logging
from typing import Dict, Any, Optional

from .base import (
    BaseSensorAdapter,
    SensorReading,
    SensorSourceType,
    ConnectionState
)

logger = logging.getLogger("NIRA.Sensors.Environment")


class EnvironmentReading(SensorReading):
    """
    Normalized environmental monitoring telemetry.
    """
    def __init__(
        self,
        sensor_id: str,
        source_type: SensorSourceType,
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        ambient_light_lux: Optional[float] = None,
        noise_level_db: Optional[float] = None,
        wet_floor_detected: bool = False,
        air_quality_index: Optional[float] = None,
        is_valid: bool = True,
        error_message: Optional[str] = None,
        zone: str = "bathroom",
        raw_metadata: Optional[Dict[str, Any]] = None
    ):
        data = {
            "temperature_c": temperature_c,
            "humidity_percent": humidity_percent,
            "ambient_light_lux": ambient_light_lux,
            "noise_level_db": noise_level_db,
            "wet_floor_detected": wet_floor_detected,
            "air_quality_index": air_quality_index
        }
        super().__init__(
            sensor_id=sensor_id,
            sensor_type="environment",
            source_type=source_type,
            data=data,
            is_valid=is_valid,
            error_message=error_message,
            zone=zone,
            metadata=raw_metadata or {}
        )
        self.temperature_c = temperature_c
        self.humidity_percent = humidity_percent
        self.ambient_light_lux = ambient_light_lux
        self.noise_level_db = noise_level_db
        self.wet_floor_detected = wet_floor_detected
        self.air_quality_index = air_quality_index


class BaseEnvironmentAdapter(BaseSensorAdapter):
    """Base class for ambient environment sensors."""
    def __init__(
        self,
        sensor_id: str = "env_node_bathroom",
        source_type: SensorSourceType = SensorSourceType.UNAVAILABLE,
        zone: str = "bathroom",
        ingest_stream: Optional[Any] = None
    ):
        super().__init__(
            sensor_id=sensor_id,
            sensor_type="environment",
            source_type=source_type,
            zone=zone,
            ingest_stream=ingest_stream
        )


class RealEnvironmentAdapter(BaseEnvironmentAdapter):
    """
    Physical environmental sensor adapter (Zigbee / MQTT / I2C / Serial / BLE).
    Reads real temperature, moisture sensors, and ambient light detectors.
    """

    def __init__(
        self,
        sensor_id: str = "env_hw_node_1",
        interface: Optional[str] = None,
        zone: str = "bathroom",
        ingest_stream: Optional[Any] = None
    ):
        super().__init__(
            sensor_id=sensor_id,
            source_type=SensorSourceType.REAL_HARDWARE,
            zone=zone,
            ingest_stream=ingest_stream
        )
        self.interface = interface
        self._connected = False
        self._packet_buffer: Optional[Dict[str, Any]] = None

    def connect(self) -> bool:
        if not self.interface:
            logger.info(f"Real Environment [{self.sensor_id}]: No direct bus defined. Standby for gateway packet injection.")
            self.connection_state = ConnectionState.CONNECTED
            self._connected = True
            return True

        try:
            logger.info(f"Connecting to environmental bus at {self.interface}...")
            self.connection_state = ConnectionState.CONNECTED
            self._connected = True
            return True
        except Exception as e:
            self.last_error = f"Environment sensor bus error: {e}"
            self.connection_state = ConnectionState.ERROR
            self.publish_sensor_health_event("BUS_CONNECT_FAILED", {"error": str(e)})
            return False

    def disconnect(self):
        self._connected = False
        self.connection_state = ConnectionState.DISCONNECTED
        self.publish_sensor_health_event("DISCONNECTED")

    def ingest_raw_packet(self, data: Dict[str, Any]):
        """Injects reading from Zigbee / MQTT physical gateway."""
        self._packet_buffer = data
        self.connection_state = ConnectionState.CONNECTED
        self._connected = True

    def read(self) -> EnvironmentReading:
        now = time.time()
        self.last_reading_time = now

        if not self._connected and not self._packet_buffer:
            self.last_error = "Environment sensor disconnected"
            self.connection_state = ConnectionState.DISCONNECTED
            self.publish_sensor_health_event("DEVICE_DISCONNECTED")
            return EnvironmentReading(
                sensor_id=self.sensor_id,
                source_type=SensorSourceType.REAL_HARDWARE,
                is_valid=False,
                error_message="Physical environmental sensor disconnected",
                zone=self.zone
            )

        try:
            self._readings_count += 1
            if self._packet_buffer:
                p = self._packet_buffer
                self._packet_buffer = None
                return EnvironmentReading(
                    sensor_id=self.sensor_id,
                    source_type=SensorSourceType.REAL_HARDWARE,
                    temperature_c=float(p["temperature_c"]) if "temperature_c" in p else None,
                    humidity_percent=float(p["humidity_percent"]) if "humidity_percent" in p else None,
                    ambient_light_lux=float(p["ambient_light_lux"]) if "ambient_light_lux" in p else None,
                    noise_level_db=float(p["noise_level_db"]) if "noise_level_db" in p else None,
                    wet_floor_detected=bool(p.get("wet_floor_detected", False)),
                    air_quality_index=float(p["air_quality_index"]) if "air_quality_index" in p else None,
                    is_valid=True,
                    zone=self.zone,
                    raw_metadata={"bus": "physical_env_gateway", "raw": p}
                )

            return EnvironmentReading(
                sensor_id=self.sensor_id,
                source_type=SensorSourceType.REAL_HARDWARE,
                is_valid=True,
                zone=self.zone,
                raw_metadata={"status": "awaiting_telemetry"}
            )
        except Exception as e:
            self.last_error = f"Malformed environment reading: {e}"
            return EnvironmentReading(
                sensor_id=self.sensor_id,
                source_type=SensorSourceType.REAL_HARDWARE,
                is_valid=False,
                error_message=str(e),
                zone=self.zone
            )


class SimulatedEnvironmentAdapter(BaseEnvironmentAdapter):
    """
    Explicit Environment Simulator.
    Simulates ambient temperature, humidity, lux, and wet-floor conditions.
    Strictly reports source_type: SensorSourceType.SIMULATED.
    """

    def __init__(
        self,
        sensor_id: str = "env_node_sim",
        zone: str = "bathroom",
        temp_c: float = 22.5,
        humidity: float = 58.0,
        lux: float = 240.0,
        wet_floor: bool = False,
        ingest_stream: Optional[Any] = None
    ):
        super().__init__(
            sensor_id=sensor_id,
            source_type=SensorSourceType.SIMULATED,
            zone=zone,
            ingest_stream=ingest_stream
        )
        self.temp_c = temp_c
        self.humidity = humidity
        self.lux = lux
        self.wet_floor = wet_floor
        self.connection_state = ConnectionState.SIMULATED
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        self.connection_state = ConnectionState.SIMULATED
        return True

    def disconnect(self):
        self._connected = False
        self.connection_state = ConnectionState.DISCONNECTED

    def read(self) -> EnvironmentReading:
        now = time.time()
        self.last_reading_time = now

        if not self._connected:
            return EnvironmentReading(
                sensor_id=self.sensor_id,
                source_type=SensorSourceType.SIMULATED,
                is_valid=False,
                error_message="Simulated environment sensor offline",
                zone=self.zone
            )

        self._readings_count += 1
        return EnvironmentReading(
            sensor_id=self.sensor_id,
            source_type=SensorSourceType.SIMULATED,
            temperature_c=self.temp_c,
            humidity_percent=self.humidity,
            ambient_light_lux=self.lux,
            noise_level_db=38.5,
            wet_floor_detected=self.wet_floor,
            air_quality_index=32.0,
            is_valid=True,
            zone=self.zone,
            raw_metadata={"simulator": True}
        )
