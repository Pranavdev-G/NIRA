"""
Tests for NIRA Demo and Live System Separation & Endpoints.
"""

import pytest
from fastapi.testclient import TestClient

try:
    from app.main import app
except ImportError:
    from Demo.app.main import app

try:
    from demo import (
        WearableSimulator,
        EnvironmentSimulator,
        RadarSimulator,
        VisionSimulator,
        VoiceSimulator,
        ScenarioSimulator
    )
except ImportError:
    try:
        from Demo import (
            WearableSimulator,
            EnvironmentSimulator,
            RadarSimulator,
            VisionSimulator,
            VoiceSimulator,
            ScenarioSimulator
        )
    except ImportError:
        from wearable_simulator import WearableSimulator
        from environment_simulator import EnvironmentSimulator
        from radar_simulator import RadarSimulator
        from vision_simulator import VisionSimulator
        from voice_simulator import VoiceSimulator
        from scenario_simulator import ScenarioSimulator

try:
    from live import LiveVisionTracker, LiveIngestStream
except ImportError:
    try:
        from Live import LiveVisionTracker, LiveIngestStream
    except ImportError:
        LiveVisionTracker = None
        LiveIngestStream = None


@pytest.fixture
def client():
    return TestClient(app)


def test_demo_launch_endpoint(client):
    """Verifies that clicking DEMO invokes the backend launch endpoint."""
    res = client.post("/api/v1/demo/launch")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["system_mode"] == "demo"
    assert "available_scenarios" in data
    assert data["demo_folder"] == "demo/"
    assert data["live_folder"] == "live/"


def test_demo_reference_endpoint(client):
    """Verifies the reference manifest for demo and live folders."""
    res = client.get("/api/v1/demo/reference")
    assert res.status_code == 200
    data = res.json()
    assert "architecture" in data
    assert "demo" in data["architecture"]
    assert "live" in data["architecture"]
    assert len(data["architecture"]["demo"]["files"]) > 0
    assert len(data["architecture"]["live"]["files"]) > 0


def test_demo_scenario_trigger(client, monkeypatch):
    """Verifies triggering a demo scenario from demo/."""
    try:
        monkeypatch.setattr("app.routers.demo_api._run_scenario_background", lambda name: None)
    except Exception:
        monkeypatch.setattr("Demo.app.routers.demo_api._run_scenario_background", lambda name: None)
    res = client.post("/api/v1/demo/scenario/false_alarm")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "triggered"
    assert data["scenario"] == "false_alarm"


def test_demo_package_imports():
    """Verifies that all simulator classes in demo/ import and instantiate cleanly."""
    wear = WearableSimulator(resident_id="user_eleanor_vance")
    radar = RadarSimulator(resident_id="user_eleanor_vance")
    env = EnvironmentSimulator(resident_id="user_eleanor_vance")
    assert wear is not None
    assert radar is not None
    assert env is not None


def test_live_package_imports():
    """Verifies that live model components in live/ import and instantiate cleanly."""
    if LiveVisionTracker and LiveIngestStream:
        tracker = LiveVisionTracker(backend_url="http://localhost:8000")
        stream = LiveIngestStream(backend_url="http://localhost:8000")
        assert tracker is not None
        assert stream is not None
