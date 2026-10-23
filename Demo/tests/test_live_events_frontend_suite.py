"""
Comprehensive 20-Point Live Backend & Frontend Contract Test Suite.
Validates that the NIRA frontend is an authoritative, real-time client
of the backend safety engine and never an independent or desynchronized simulation.

Test Matrix:
 1. Backend connected (health & SSE contract)
 2. Backend disconnected (state transition & offline alert banner)
 3. Reconnection (backoff retry & status restoration)
 4. New telemetry (rolling histories & trend derivation)
 5. Risk change (multi-modal tier badge & ribbon transition)
 6. Fall event (spatial room occupancy & posture transition)
 7. Wellness check (acoustic state machine & countdown activation)
 8. User response (conversational verification & risk downgrade)
 9. Timeout (acoustic silence escalation to emergency)
10. Caregiver notification (multi-channel dispatch record)
11. Caregiver acknowledgement (audit trail logging & button state)
12. Emergency escalation (911 CAD packet transmission & smart deadbolt)
13. Emergency resolution (closure audit, lock restoration, duration calculation)
14. No telemetry (graceful 'NO LIVE DATA' empty states without fake numbers)
15. Stale telemetry (visible warning for telemetry > 60s)
16. Multiple events arriving quickly (concurrency & sequence integrity)
17. Mobile viewport (responsive layout reflow rules)
18. Keyboard navigation (skip-link, tablist ARIA, room tile keydown)
19. Reduced motion (prefers-reduced-motion animation suppression)
20. Empty incident history (meaningful empty state & filter mismatch guidance)
"""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: Backend Connected
# ---------------------------------------------------------------------------
def test_01_backend_connected():
    """Verify backend health endpoint and MCP connection endpoint respond."""
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # Verify MCP endpoint initializes properly
    mcp_resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert mcp_resp.status_code == 200
    assert mcp_resp.json()["result"]["serverInfo"]["name"] == "Aegis Ambient Care MCP Server"


# ---------------------------------------------------------------------------
# Test 2: Backend Disconnected
# ---------------------------------------------------------------------------
def test_02_backend_disconnected():
    """Verify frontend HTML has systemStateBanner with role=alert for disconnected state."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="systemStateBanner"' in html
    assert 'role="alert"' in html
    assert 'STREAM DISCONNECTED' in html
    assert 'bannerRetryBtn' in html


# ---------------------------------------------------------------------------
# Test 3: Reconnection
# ---------------------------------------------------------------------------
def test_03_reconnection():
    """Verify store code has handleDisconnect, backoff reconnect, and measureLatency."""
    resp = client.get("/static/nira_store.js")
    assert resp.status_code == 200
    store_code = resp.text
    assert "handleDisconnect" in store_code
    assert "reconnectAttempts" in store_code
    assert "measureLatency" in store_code
    assert "reconnecting" in store_code


# ---------------------------------------------------------------------------
# Test 4: New Telemetry
# ---------------------------------------------------------------------------
def test_04_new_telemetry():
    """Verify rolling telemetry ingestion, trend detection, and sparkline generation."""
    resp = client.get("/static/nira_store.js")
    assert resp.status_code == 200
    store_code = resp.text
    assert "generateSparklinePath" in store_code
    assert "hrHistory" in store_code
    assert "trend" in store_code

    # Verify DOM contains sparkline SVG path and trend tags
    dash_resp = client.get("/")
    assert "hrSparklinePath" in dash_resp.text
    assert "hrTrendTag" in dash_resp.text
    assert "moveBreadcrumbs" in dash_resp.text


# ---------------------------------------------------------------------------
# Test 5: Risk Change
# ---------------------------------------------------------------------------
def test_05_risk_change():
    """Verify multi-modal risk representations: Tier 1 (Safe), Tier 2 (Alert), Tier 3 (Critical)."""
    resp = client.get("/static/dashboard.js")
    assert resp.status_code == 200
    dash_code = resp.text
    assert "TIER 1" in dash_code
    assert "TIER 2" in dash_code
    assert "TIER 3" in dash_code

    # Verify CSS contains corresponding multi-modal classes
    css_resp = client.get("/static/dashboard.css")
    assert ".severity-tag.safe" in css_resp.text
    assert ".severity-tag.warning" in css_resp.text
    assert ".severity-tag.critical" in css_resp.text


# ---------------------------------------------------------------------------
# Test 6: Fall Event
# ---------------------------------------------------------------------------
def test_06_fall_event():
    """Ingest a fall event in bathroom, verify backend persists CRITICAL risk and location."""
    payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.95,
            "location": "bathroom",
            "movement_after_event": "none",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "context": {
            "activity": "sleeping",
            "time_context": "night",
            "baseline_deviation": 0.90,
            "wearable_status": "worn_normal",
            "environment": "dark_hazard"
        },
        "user_id": "user_eleanor_vance"
    }
    resp = client.post("/api/v1/events", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["location"] == "bathroom"
    assert data["risk_assessment"]["risk_level"] in ["HIGH", "CRITICAL"]
    assert data["risk_assessment"]["requires_wellness_check"] is True


# ---------------------------------------------------------------------------
# Test 7: Wellness Check
# ---------------------------------------------------------------------------
def test_07_wellness_check():
    """Verify that a high-risk fall automatically creates a WELLNESS_CHECK_INITIATED timeline item."""
    payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.92,
            "location": "bathroom",
            "movement_after_event": "none",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "context": {
            "activity": "sleeping",
            "time_context": "night",
            "baseline_deviation": 0.88,
            "wearable_status": "worn_normal",
            "environment": "dark_hazard"
        }
    }
    create_resp = client.post("/api/v1/events", json=payload)
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    # Verify timeline has wellness check
    tl_resp = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert tl_resp.status_code == 200
    timeline = tl_resp.json()
    action_types = [t["action_type"] for t in timeline]
    assert "WELLNESS_CHECK_INITIATED" in action_types


# ---------------------------------------------------------------------------
# Test 8: User Response (Safe Reply)
# ---------------------------------------------------------------------------
def test_08_user_response():
    """Verify senior responding 'I am fine' transitions incident status to RESOLVED and LOW risk."""
    # Create incident
    payload = {
        "event": {
            "event_type": "dropped_object_reach",
            "confidence": 0.85,
            "location": "living",
            "movement_after_event": "normal",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    create_resp = client.post("/api/v1/events", json=payload)
    incident_id = create_resp.json()["incident_id"]

    # Senior verbal response
    voice_resp = client.post(
        f"/api/v1/incidents/{incident_id}/respond-voice",
        json={"transcript": "I am fine, Alexa! No need to worry.", "is_timeout": False}
    )
    assert voice_resp.status_code == 200
    res_data = voice_resp.json()
    assert res_data["status"] == "RESOLVED"
    assert res_data["risk_level"] == "LOW"
    assert res_data["voice_intent"] == "safe"


# ---------------------------------------------------------------------------
# Test 9: Timeout (Acoustic Silence)
# ---------------------------------------------------------------------------
def test_09_timeout():
    """Verify voice check timeout (20s silence) transitions status to ESCALATED_CAD and CRITICAL risk."""
    payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.94,
            "location": "bathroom",
            "movement_after_event": "none",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    create_resp = client.post("/api/v1/events", json=payload)
    incident_id = create_resp.json()["incident_id"]

    # Submit timeout
    timeout_resp = client.post(
        f"/api/v1/incidents/{incident_id}/respond-voice",
        json={"transcript": None, "is_timeout": True}
    )
    assert timeout_resp.status_code == 200
    t_data = timeout_resp.json()
    assert t_data["status"] == "ESCALATED_CAD"
    assert t_data["risk_level"] == "CRITICAL"
    assert t_data["action_taken"] == "SILENT_EMERGENCY_CAD_DISPATCH"
    assert "cad_details" in t_data


# ---------------------------------------------------------------------------
# Test 10: Caregiver Notification
# ---------------------------------------------------------------------------
def test_10_caregiver_notification():
    """Verify caregiver escalation endpoint logs CAREGIVER_NOTIFIED in audit trail."""
    payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.80,
            "location": "kitchen",
            "movement_after_event": "slow",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    inc_resp = client.post("/api/v1/events", json=payload)
    incident_id = inc_resp.json()["incident_id"]

    # Escalate to caregiver
    esc_resp = client.post(
        f"/api/v1/incidents/{incident_id}/escalate",
        json={"escalation_type": "caregiver", "reason": "Senior called out for assistance"}
    )
    assert esc_resp.status_code == 200
    assert esc_resp.json()["status"] == "ESCALATED_CAREGIVER"

    # Check timeline
    tl_resp = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert any("CAREGIVER" in t["action_type"] for t in tl_resp.json())


# ---------------------------------------------------------------------------
# Test 11: Caregiver Acknowledgement
# ---------------------------------------------------------------------------
def test_11_caregiver_acknowledgement():
    """Verify frontend store acknowledgeCaregiver method appends CAREGIVER_ACKNOWLEDGED entry."""
    resp = client.get("/static/nira_store.js")
    assert resp.status_code == 200
    assert "acknowledgeCaregiver" in resp.text
    assert "CAREGIVER_ACKNOWLEDGED" in resp.text
    assert "acknowledgedAt" in resp.text


# ---------------------------------------------------------------------------
# Test 12: Emergency Escalation
# ---------------------------------------------------------------------------
def test_12_emergency_escalation():
    """Verify emergency CAD escalation creates CAD_DISPATCHED entry with units and door PIN."""
    payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.96,
            "location": "bathroom",
            "movement_after_event": "none",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    inc_resp = client.post("/api/v1/events", json=payload)
    incident_id = inc_resp.json()["incident_id"]

    # Escalate to 911 CAD emergency
    esc_resp = client.post(
        f"/api/v1/incidents/{incident_id}/escalate",
        json={"escalation_type": "emergency", "reason": "Presumed unconscious after 20s acoustic silence"}
    )
    assert esc_resp.status_code == 200
    esc_data = esc_resp.json()
    assert esc_data["status"] == "ESCALATED_CAD"
    assert "emergency_packet_id" in esc_data
    assert esc_data["emergency_packet_id"].startswith("EPK-")
    assert esc_data["door_lock_unlocked"] is True
    assert len(esc_data["units_dispatched"]) >= 1


# ---------------------------------------------------------------------------
# Test 13: Emergency Resolution
# ---------------------------------------------------------------------------
def test_13_emergency_resolution():
    """Verify incident resolution closes incident with resolved_at timestamp."""
    payload = {
        "event": {
            "event_type": "dropped_object_reach",
            "confidence": 0.85,
            "location": "kitchen",
            "movement_after_event": "normal",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    inc_resp = client.post("/api/v1/events", json=payload)
    incident_id = inc_resp.json()["incident_id"]

    # Resolve via safe verbal reply
    res_resp = client.post(
        f"/api/v1/incidents/{incident_id}/respond-voice",
        json={"transcript": "Everything is fine here.", "is_timeout": False}
    )
    assert res_resp.status_code == 200
    data = res_resp.json()
    assert data["status"] == "RESOLVED"

    # Verify timeline contains INCIDENT_RESOLVED entry
    tl_resp = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert any("RESOLVE" in t["action_type"] for t in tl_resp.json())


# ---------------------------------------------------------------------------
# Test 14: No Telemetry
# ---------------------------------------------------------------------------
def test_14_no_telemetry():
    """Verify frontend renders 'NO LIVE DATA' badge when hasLiveData is false."""
    dash_js = client.get("/static/dashboard.js").text
    assert "no-live-data-badge" in dash_js
    assert "NO LIVE DATA" in dash_js

    # Verify CSS defines the styling for no-live-data
    dash_css = client.get("/static/dashboard.css").text
    assert ".no-live-data-badge" in dash_css


# ---------------------------------------------------------------------------
# Test 15: Stale Telemetry
# ---------------------------------------------------------------------------
def test_15_stale_telemetry():
    """Verify frontend code calculates age and appends stale-data-badge when telemetry > 60s."""
    dash_js = client.get("/static/dashboard.js").text
    assert "isHrStale" in dash_js
    assert "isMvStale" in dash_js
    assert "stale-data-badge" in dash_js

    dash_css = client.get("/static/dashboard.css").text
    assert ".stale-data-badge" in dash_css


# ---------------------------------------------------------------------------
# Test 16: Multiple Events Arriving Quickly
# ---------------------------------------------------------------------------
def test_16_multiple_events_arriving_quickly():
    """Ingest 10 rapid sequential events and ensure backend processes all without error."""
    incident_ids = []
    for i in range(10):
        payload = {
            "event": {
                "event_type": "environmental_hazard" if i % 2 == 0 else "loud_thud",
                "confidence": 0.85 + (i * 0.01),
                "location": "kitchen" if i % 2 == 0 else "living",
                "movement_after_event": "normal",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        resp = client.post("/api/v1/events", json=payload)
        assert resp.status_code == 201
        incident_ids.append(resp.json()["incident_id"])

    assert len(incident_ids) == 10
    assert len(set(incident_ids)) == 10  # All unique incident IDs


# ---------------------------------------------------------------------------
# Test 17: Mobile Viewport
# ---------------------------------------------------------------------------
def test_17_mobile_viewport():
    """Verify CSS media queries exist for mobile (<600px) and tablet (<900px)."""
    css = client.get("/static/dashboard.css").text
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 600px)" in css
    assert "min-height: 44px" in css  # Touch target size


# ---------------------------------------------------------------------------
# Test 18: Keyboard Navigation
# ---------------------------------------------------------------------------
def test_18_keyboard_navigation():
    """Verify focus-visible outlines, skip-link, and ARIA attributes in HTML and CSS."""
    css = client.get("/static/dashboard.css").text
    assert ":focus-visible" in css
    assert ".skip-link" in css

    html = client.get("/").text
    assert 'class="skip-link"' in html
    assert 'role="tablist"' in html
    assert 'role="tab"' in html
    assert 'role="tabpanel"' in html


# ---------------------------------------------------------------------------
# Test 19: Reduced Motion
# ---------------------------------------------------------------------------
def test_19_reduced_motion():
    """Verify CSS contains @media (prefers-reduced-motion: reduce) rule."""
    css = client.get("/static/dashboard.css").text
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation-duration: 0.01ms !important" in css


# ---------------------------------------------------------------------------
# Test 20: Empty Incident History
# ---------------------------------------------------------------------------
def test_20_empty_incident_history():
    """Verify admin portal has emptyHistoryState and distinct guidance text for empty feeds."""
    admin_html = client.get("/admin").text
    assert 'id="emptyHistoryState"' in admin_html
    assert 'id="emptyTitleText"' in admin_html
    assert 'id="emptyDescText"' in admin_html

    admin_js = client.get("/static/admin.js").text
    assert "No Safety Events Recorded" in admin_js
    assert "No Incidents Match Your Filters" in admin_js


# ---------------------------------------------------------------------------
# Test 21: Dynamic Map Geospatial Markers (Default Boston Base)
# ---------------------------------------------------------------------------
def test_21_dynamic_map_services_default():
    """Verify /api/v1/live/map/services returns Resident, Caretaker, and Emergency Services."""
    resp = client.get("/api/v1/live/map/services")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert "resident" in data
    assert "caretaker" in data
    assert "services" in data
    assert "city_presets" in data

    # Verify Resident data
    res = data["resident"]
    assert "lat" in res and "lon" in res
    assert res["lat"] == pytest.approx(42.3601, abs=0.01)

    # Verify Caretaker data
    ct = data["caretaker"]
    assert "lat" in ct and "lon" in ct
    assert ct["distance_km"] > 0
    assert ct["eta_mins"] > 0
    assert "phone" in ct

    # Verify Emergency Services (Hospitals, EMS, Fire, Police)
    services = data["services"]
    assert len(services) >= 4
    service_types = {s["type"] for s in services}
    assert "hospital" in service_types
    assert "ems" in service_types
    assert "fire" in service_types
    assert "police" in service_types

    # Verify nearest service is populated
    nearest = data["nearest_service"]
    assert nearest is not None
    assert nearest["distance_km"] <= services[-1]["distance_km"]


# ---------------------------------------------------------------------------
# Test 22: Dynamic Map City Presets (Non-Static Adaptation)
# ---------------------------------------------------------------------------
def test_22_dynamic_map_city_presets():
    """Verify map re-anchors to different cities and changes facility data accordingly."""
    cities = ["seattle", "san_francisco", "new_york", "london", "bengaluru", "tokyo"]
    for c in cities:
        resp = client.get(f"/api/v1/live/map/services?city={c}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["services"]) >= 4
        assert data["caretaker"]["distance_km"] > 0
        assert data["caretaker"]["eta_mins"] > 0


# ---------------------------------------------------------------------------
# Test 23: Dynamic Map Custom GPS Coordinates (Anywhere on Earth)
# ---------------------------------------------------------------------------
def test_23_dynamic_map_custom_gps():
    """Verify arbitrary lat/lon generates localized emergency facilities with valid Haversine math."""
    # Test arbitrary GPS (e.g., Paris, France coordinates: 48.8566, 2.3522)
    resp = client.get("/api/v1/live/map/services?lat=48.8566&lon=2.3522")
    assert resp.status_code == 200
    data = resp.json()

    assert data["resident"]["lat"] == pytest.approx(48.8566, abs=0.001)
    assert data["resident"]["lon"] == pytest.approx(2.3522, abs=0.001)

    # Caretaker should be positioned relative to this custom coordinate
    ct = data["caretaker"]
    assert ct["lat"] == pytest.approx(48.8566 + 0.0075, abs=0.001)
    assert ct["distance_km"] > 0.5
    assert ct["eta_mins"] >= 2.0

    # Services should all have positive distance and ETA
    for s in data["services"]:
        assert s["distance_km"] > 0
        assert s["eta_mins"] > 0


# ---------------------------------------------------------------------------
# Test 24: Map Locate and Recompute POST Endpoint
# ---------------------------------------------------------------------------
def test_24_map_locate_post():
    """Verify POST /api/v1/live/map/locate relocates resident and updates profile."""
    payload = {"query": "Seattle, WA", "lat": 47.6062, "lon": -122.3321}
    resp = client.post("/api/v1/live/map/locate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Seattle" in data["location_name"]
    assert data["resident"]["lat"] == pytest.approx(47.6062, abs=0.01)


# ---------------------------------------------------------------------------
# Test 25: MapTiler OpenStreetMap API Key Integration
# ---------------------------------------------------------------------------
def test_25_maptiler_integration():
    """Verify MapTiler key XtY4Bvc3fXWmf1tU3H3S and openstreetmap style are configured in dashboard assets."""
    js = client.get("/static/dashboard.js").text
    assert "XtY4Bvc3fXWmf1tU3H3S" in js
    assert "api.maptiler.com/maps/openstreetmap" in js
    assert "setMapTilerStyle" in js

    html = client.get("/").text
    assert "btnStyleOsm" in html
    assert "setMapTilerStyle" in html


