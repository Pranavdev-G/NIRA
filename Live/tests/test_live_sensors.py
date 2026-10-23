"""
Unit Tests for NIRA Live Sensor Adapters.
Amazon Developer Hackathon 2026.

Validates:
  - Provenance separation: REAL_HARDWARE / REAL_WEARABLE vs SIMULATED
  - Wearable adapter (heart rate, SpO2, connection states)
  - Radar adapter (60GHz presence, motion, distance, fall signatures)
  - Environment adapter (temperature, humidity, lux, wet floor)
  - GPS location evidence adapter (coordinates, accuracy, fix status)
  - Non-crashing hardware failure behavior (disconnect, timeout, malformed packets)
"""

import pytest
from Live.sensors.base import (
    SensorSourceType,
    ConnectionState,
    SensorReading
)
from Live.sensors.wearable import (
    RealWearableAdapter,
    SimulatedWearableAdapter,
    WearableReading
)
from Live.sensors.radar import (
    RealRadarAdapter,
    SimulatedRadarAdapter,
    RadarReading
)
from Live.sensors.environment import (
    RealEnvironmentAdapter,
    SimulatedEnvironmentAdapter,
    EnvironmentReading
)
from Live.sensors.gps import (
    RealGPSAdapter,
    SimulatedGPSAdapter,
    GPSReading
)


# ============================================================================
# 1. Wearable Adapter Tests
# ============================================================================

def test_simulated_wearable_provenance():
    """Simulated wearable must be strictly labeled as SIMULATED."""
    sim = SimulatedWearableAdapter(sensor_id="sim_band_1", base_hr=70.0)
    sim.connect()
    reading = sim.read()

    assert reading.source_type == SensorSourceType.SIMULATED
    assert reading.is_valid is True
    assert reading.heart_rate_bpm is not None
    assert 60.0 <= reading.heart_rate_bpm <= 85.0
    assert reading.metadata.get("simulator") is True


def test_real_wearable_packet_ingestion():
    """Real wearable must be labeled REAL_WEARABLE and ingest hardware packets."""
    hw = RealWearableAdapter(sensor_id="pulse_band_hw_1")
    hw.connect()

    hw.ingest_raw_packet({"heart_rate_bpm": 74.0, "spo2_percent": 99.0, "battery_percent": 90.0})
    reading = hw.read()

    assert reading.source_type == SensorSourceType.REAL_WEARABLE
    assert reading.heart_rate_bpm == 74.0
    assert reading.spo2_percent == 99.0
    assert reading.is_valid is True


def test_real_wearable_disconnected_produces_health_not_crash():
    """Disconnected wearable must return invalid reading without crashing."""
    hw = RealWearableAdapter(sensor_id="pulse_band_hw_2")
    hw.disconnect()

    reading = hw.read()
    assert reading.is_valid is False
    assert reading.device_connected is False
    assert "disconnected" in reading.error_message.lower()


def test_real_wearable_malformed_packet_handling():
    """Malformed packets must be handled gracefully without throwing unhandled exceptions."""
    hw = RealWearableAdapter(sensor_id="pulse_band_hw_3")
    hw.connect()
    hw.ingest_raw_packet({"heart_rate_bpm": "NOT_A_NUMBER"})

    reading = hw.read()
    assert reading.is_valid is False
    assert "malformed" in reading.error_message.lower()


# ============================================================================
# 2. Radar Adapter Tests
# ============================================================================

def test_simulated_radar_provenance():
    """Simulated radar must be strictly labeled as SIMULATED."""
    sim_radar = SimulatedRadarAdapter(presence=True, motion=0.45, distance_m=2.1)
    sim_radar.connect()
    reading = sim_radar.read()

    assert reading.source_type == SensorSourceType.SIMULATED
    assert reading.presence_detected is True
    assert reading.motion_intensity == 0.45
    assert reading.target_distance_m == 2.1
    assert reading.metadata.get("simulator") is True


def test_real_radar_packet_ingestion():
    """Real radar must ingest hardware frames and report REAL_HARDWARE."""
    hw_radar = RealRadarAdapter(sensor_id="mmwave_hw_1")
    hw_radar.connect()

    hw_radar.ingest_raw_packet({
        "presence": True,
        "motion": 0.88,
        "distance_m": 1.5,
        "fall_signature": True,
        "respiration": 18.0
    })
    reading = hw_radar.read()

    assert reading.source_type == SensorSourceType.REAL_HARDWARE
    assert reading.presence_detected is True
    assert reading.fall_signature_detected is True
    assert reading.respiration_rate_bpm == 18.0


def test_real_radar_disconnected_produces_health_not_crash():
    """Disconnected radar returns invalid reading and emits health event without crashing."""
    hw_radar = RealRadarAdapter(sensor_id="mmwave_hw_2")
    hw_radar.disconnect()

    reading = hw_radar.read()
    assert reading.is_valid is False
    assert reading.source_type == SensorSourceType.REAL_HARDWARE


# ============================================================================
# 3. Environment Adapter Tests
# ============================================================================

def test_simulated_environment_provenance():
    """Simulated environment readings must be labeled SIMULATED."""
    sim_env = SimulatedEnvironmentAdapter(temp_c=23.5, humidity=45.0, lux=300.0, wet_floor=True)
    sim_env.connect()
    reading = sim_env.read()

    assert reading.source_type == SensorSourceType.SIMULATED
    assert reading.temperature_c == 23.5
    assert reading.wet_floor_detected is True


def test_real_environment_packet_ingestion():
    """Real environment adapter ingests gateway telemetry."""
    hw_env = RealEnvironmentAdapter(sensor_id="env_hw_node")
    hw_env.connect()

    hw_env.ingest_raw_packet({
        "temperature_c": 21.0,
        "humidity_percent": 55.0,
        "ambient_light_lux": 180.0,
        "wet_floor_detected": False
    })
    reading = hw_env.read()

    assert reading.source_type == SensorSourceType.REAL_HARDWARE
    assert reading.temperature_c == 21.0
    assert reading.wet_floor_detected is False


def test_real_environment_disconnected_not_crash():
    """Disconnected environmental node handles read gracefully."""
    hw_env = RealEnvironmentAdapter(sensor_id="env_hw_node_disc")
    hw_env.disconnect()

    reading = hw_env.read()
    assert reading.is_valid is False


# ============================================================================
# 4. GPS Location Adapter Tests
# ============================================================================

def test_simulated_gps_provenance():
    """Simulated GPS must declare SIMULATED and never masquerade as physical receiver."""
    sim_gps = SimulatedGPSAdapter(latitude=37.7749, longitude=-122.4194)
    sim_gps.connect()
    reading = sim_gps.read()

    assert reading.source_type == SensorSourceType.SIMULATED
    assert reading.availability == "SIMULATED_FIX"
    assert reading.latitude == 37.7749
    assert reading.longitude == -122.4194


def test_real_gps_packet_ingestion():
    """Real GPS adapter ingests NMEA/GNSS fixes."""
    hw_gps = RealGPSAdapter(sensor_id="gnss_hw_1")
    hw_gps.connect()

    hw_gps.ingest_raw_packet({
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_m": 3.2,
        "availability": "3D_FIX"
    })
    reading = hw_gps.read()

    assert reading.source_type == SensorSourceType.REAL_HARDWARE
    assert reading.latitude == 40.7128
    assert reading.availability == "3D_FIX"
    assert reading.is_valid is True


def test_real_gps_disconnected_handling():
    """Disconnected GPS returns invalid fix without crashing."""
    hw_gps = RealGPSAdapter(sensor_id="gnss_hw_2")
    hw_gps.disconnect()

    reading = hw_gps.read()
    assert reading.is_valid is False
    assert reading.availability == "UNAVAILABLE"


# ============================================================================
# 5. Conversion to Normalized Live Events
# ============================================================================

def test_sensor_reading_to_live_event():
    """Every sensor reading must convert cleanly to a normalized NIRA live event."""
    reading = WearableReading(
        sensor_id="pulse_band_test",
        source_type=SensorSourceType.REAL_WEARABLE,
        heart_rate_bpm=76.0,
        spo2_percent=98.0,
        zone="bedroom"
    )
    evt = reading.to_live_event(resident_id="resident_live", correlation_id="corr_test_1")

    assert evt["event_id"] is not None
    assert evt["event_type"] == "WEARABLE_READING"
    assert evt["source"] == "live_wearable"
    assert evt["zone"] == "bedroom"
    assert evt["resident_id"] == "resident_live"
    assert evt["correlation_id"] == "corr_test_1"
    assert evt["payload"]["reading"]["heart_rate_bpm"] == 76.0
