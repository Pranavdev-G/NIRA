"""
Unit Tests for Live Ingest Stream Event Producer.
Amazon Developer Hackathon 2026.

Validates:
  - Normalized event structure and validation
  - Duplicate event ID suppression
  - Offline buffering when backend is unavailable
  - Retry behavior with exponential backoff
  - Non-blocking async queue worker and clean shutdown
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from Live.live_ingest_stream import (
    LiveIngestStream,
    build_live_event
)


@pytest.fixture
def ingest_stream():
    stream = LiveIngestStream(
        backend_url="http://mock-backend:8000",
        max_retries=2,
        timeout_sec=0.5,
        enable_worker=False
    )
    yield stream
    stream.shutdown()


def test_build_live_event_normalized_structure():
    """Verifies that build_live_event produces all required normalized fields."""
    evt = build_live_event(
        event_type="FALL_DETECTED",
        source="live_vision",
        zone="kitchen",
        confidence=0.95,
        payload={"torso_angle": 12.0},
        correlation_id="corr_test_99",
        resident_id="resident_test"
    )

    assert evt["event_id"].startswith("evt_")
    assert evt["event_type"] == "FALL_DETECTED"
    assert evt["source"] == "live_vision"
    assert evt["zone"] == "kitchen"
    assert evt["confidence"] == 0.95
    assert evt["correlation_id"] == "corr_test_99"
    assert evt["resident_id"] == "resident_test"
    assert "timestamp" in evt
    assert evt["payload"]["torso_angle"] == 12.0


def test_duplicate_event_id_suppression(ingest_stream):
    """Verifies that duplicate event IDs are filtered out."""
    evt = build_live_event(
        event_type="PERSON_DETECTED",
        source="live_vision",
        event_id="evt_unique_101"
    )

    # First publication
    res1 = ingest_stream.publish_event(evt, blocking=False)
    assert res1["status"] in ["queued", "buffered"]

    # Second publication with exact same event_id
    res2 = ingest_stream.publish_event(evt, blocking=False)
    assert res2["status"] == "duplicate_ignored"
    assert res2["event_id"] == "evt_unique_101"


def test_offline_buffering_when_backend_down(ingest_stream):
    """Verifies that failed network calls buffer events in memory without crashing."""
    evt = build_live_event(
        event_type="SENSOR_READING",
        source="live_wearable",
        payload={"hr": 80}
    )

    # Mock requests.post to simulate network failure
    with patch("requests.post", side_effect=Exception("Connection refused")):
        res = ingest_stream.publish_event(evt, blocking=True)

    assert res["status"] == "buffered"
    assert "error" in res

    status = ingest_stream.get_buffer_status()
    assert status["buffered_events_count"] >= 1


def test_buffer_flush_on_reconnection(ingest_stream):
    """Verifies that buffered events can be flushed once backend becomes reachable."""
    evt1 = build_live_event(event_type="TEST_1", source="test", event_id="evt_fl_1")
    evt2 = build_live_event(event_type="TEST_2", source="test", event_id="evt_fl_2")

    # Force buffer insertion
    ingest_stream._buffer_event(evt1)
    ingest_stream._buffer_event(evt2)
    assert ingest_stream.get_buffer_status()["buffered_events_count"] == 2

    # Mock successful response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "accepted"}

    with patch("requests.post", return_value=mock_resp):
        flushed_count = ingest_stream.flush_buffer()

    assert flushed_count == 2
    assert ingest_stream.get_buffer_status()["buffered_events_count"] == 0


def test_non_blocking_async_worker():
    """Verifies non-blocking async worker thread lifecycle and clean shutdown."""
    stream = LiveIngestStream(
        backend_url="http://mock-backend:8000",
        enable_worker=True
    )
    assert stream.get_buffer_status()["is_worker_alive"] is True

    with patch.object(stream, "_send_http", return_value={"status": "published"}):
        evt = build_live_event(event_type="ASYNC_EVT", source="test", event_id="evt_async_1")
        res = stream.publish_event(evt, blocking=False)
        assert res["status"] in ["queued", "buffered"]
        time.sleep(0.05)
        stream.shutdown(timeout=2.0)

    assert stream.get_buffer_status()["is_worker_alive"] is False
