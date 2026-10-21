"""
Unit and Integration Tests for Person 2 Demo Module.
Amazon Developer Hackathon 2026.

Validates that:
1. Static assets for Person 2 demo module (demo_module.js, index.html) are properly mounted and served.
2. All 7 assigned demo pages/views exist with required DOM IDs, buttons, and state containers.
3. Fall detection simulation, emergency alert workflow, daily check-in, map, notifications, and incident history
   contain all contractual elements and workflow hooks.
4. CSS styling and Leaflet integrations are correctly referenced.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_demo_module_js_served():
    """Verify demo_module.js is accessible and contains Person 2 store and controllers."""
    resp = client.get("/static/demo_module.js")
    assert resp.status_code == 200
    text = resp.text
    assert "Person2DemoStore" in text
    assert "simulateFall" in text
    assert "acknowledgeIncident" in text
    assert "cancelIncident" in text
    assert "submitDailyCheckin" in text
    assert "VoiceAssistantController" in text
    assert "DailyCheckinController" in text
    assert "FallSimulationController" in text
    assert "EmergencyAlertController" in text
    assert "LocationMapController" in text
    assert "NotificationCenterController" in text
    assert "IncidentHistoryController" in text


def test_index_html_has_all_seven_demo_views():
    """Verify index.html contains navigation buttons and panels for all 7 Person 2 pages."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # 1. Navigation buttons
    assert 'id="tabBtnVoiceAssistant"' in html
    assert 'id="tabBtnDailyCheckin"' in html
    assert 'id="tabBtnFallDetection"' in html
    assert 'id="tabBtnEmergencyAlert"' in html
    assert 'id="tabBtnLocationMap"' in html
    assert 'id="tabBtnNotificationCenter"' in html
    assert 'id="tabBtnIncidentHistory"' in html

    # 2. Tab content panels
    assert 'id="panelVoiceAssistant"' in html
    assert 'id="panelDailyCheckin"' in html
    assert 'id="panelFallDetection"' in html
    assert 'id="panelEmergencyAlert"' in html
    assert 'id="panelLocationMap"' in html
    assert 'id="panelNotificationCenter"' in html
    assert 'id="panelIncidentHistory"' in html

    # 3. Header integration
    assert 'id="btnHeaderNotif"' in html
    assert 'id="headerNotifBadge"' in html
    assert 'id="btnHeaderResetDemo"' in html

    # 4. Leaflet map integration & fallback
    assert "leaflet.css" in html
    assert "leaflet.js" in html
    assert 'id="demoMapContainer"' in html
    assert 'id="demoHospitalCardsGrid"' in html

    # 5. Incident detail modal
    assert 'id="demoIncidentDetailModal"' in html
    assert 'demo_module.js' in html


def test_voice_assistant_elements():
    """Verify Voice Assistant has microphone toggle, transcription, and history list."""
    resp = client.get("/")
    html = resp.text
    assert 'id="demoMicToggleBtn"' in html
    assert 'id="demoLiveTranscriptionBox"' in html
    assert 'id="demoVoiceHistoryList"' in html
    assert 'id="demoVoiceInput"' in html


def test_daily_checkin_elements():
    """Verify Daily Check-in has options ('I\'m fine', 'Feeling unwell', 'Need assistance') and history table."""
    resp = client.get("/")
    html = resp.text
    assert 'data-status="fine"' in html
    assert 'data-status="unwell"' in html
    assert 'data-status="assistance"' in html
    assert 'id="demoCheckinNotes"' in html
    assert 'id="demoCheckinConfirmation"' in html
    assert 'id="demoCheckinHistoryTableBody"' in html


def test_fall_detection_elements():
    """Verify Fall Detection has Simulate Fall button and sensor matrix."""
    resp = client.get("/")
    html = resp.text
    assert 'id="btnTriggerFallSimulation"' in html
    assert 'id="demoSensorAccel"' in html
    assert 'id="demoSensorVelocity"' in html
    assert 'id="demoSensorPosture"' in html
    assert 'id="demoSensorHeartRate"' in html
    assert 'id="demoFallIncidentResultBanner"' in html


def test_emergency_alert_elements():
    """Verify Emergency Alert screen has dynamic content area."""
    resp = client.get("/")
    html = resp.text
    assert 'id="demoEmergencyAlertContent"' in html


def test_notification_center_elements():
    """Verify Notification Center has filters and notification list."""
    resp = client.get("/")
    html = resp.text
    assert 'id="demoNotificationList"' in html
    assert 'id="demoNotifUnreadCount"' in html
    assert 'data-category="emergency"' in html
    assert 'data-category="check_in"' in html


def test_incident_history_elements():
    """Verify Incident History has filters and table body."""
    resp = client.get("/")
    html = resp.text
    assert 'id="demoIncidentHistoryTableBody"' in html
    assert 'id="demoHistTypeFilter"' in html
    assert 'id="demoHistStatusFilter"' in html


def test_demo_video_guide_elements():
    """Verify Demo Video Guide elements exist on frontend."""
    resp = client.get("/")
    html = resp.text
    assert 'id="tabBtnDemoVideo"' in html
    assert 'id="panelDemoVideo"' in html
    assert 'id="demoVideoPlayerContainer"' in html
    assert 'id="btnHeaderDemoVideo"' in html

    # Verify demo_module.js contains DemoVideoController
    js = client.get("/static/demo_module.js").text
    assert "DemoVideoController" in js
    assert "demoVideoController" in js


def test_ambulance_mode_and_profile_selection():
    """Verify profile selector and ambulance CAD mode elements."""
    resp = client.get("/")
    html = resp.text
    assert "David Vance (Son • Family Admin)" in html
    assert "Eleanor & Family (Home View)" in html
    assert "Medic 14 (Boston EMS First Responder)" in html
    assert "Ambulance CAD" in html
    assert "Smart Door Token: 8492" in html

