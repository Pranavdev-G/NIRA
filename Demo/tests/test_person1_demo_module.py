"""
Unit and Integration Tests for Person 1 Demo Module.
Amazon Developer Hackathon 2026.

Validates that:
1. Static assets for Person 1 demo module (person1_module.js, login.html, index.html) are properly mounted and served.
2. Login and Signup experience exists with friendly demo logins (Eleanor Vance & David Vance) and validation.
3. All 4 Person 1 demo views (Home Dashboard, Caregiver Dashboard, Elderly Profile, Medication Reminders)
   exist with required DOM IDs, action buttons, metrics, and state containers.
4. Shared store methods (medications and resident profile updates) exist and integrate seamlessly with Person 2 state.
5. Person 2 demo pages remain fully functional and intact.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_person1_module_js_served():
    """Verify person1_module.js is accessible and contains Person 1 controllers."""
    resp = client.get("/static/person1_module.js")
    assert resp.status_code == 200
    text = resp.text
    assert "HomeDashboardController" in text
    assert "CaregiverDashboardController" in text
    assert "ElderlyProfileController" in text
    assert "MedicationRemindersController" in text
    assert "DemoAuthController" in text
    assert "markTaken" in text
    assert "markMissed" in text
    assert "saveProfile" in text
    assert "loginAsResident" in text
    assert "loginAsCaregiver" in text


def test_demo_module_js_has_person1_store_extensions():
    """Verify demo_module.js includes medication and resident profile store methods."""
    resp = client.get("/static/demo_module.js")
    assert resp.status_code == 200
    text = resp.text
    assert "markMedicationTaken" in text
    assert "markMedicationMissed" in text
    assert "addMedication" in text
    assert "updateResidentProfile" in text
    assert "window.person1Store" in text


def test_login_page_served_and_contains_auth_elements():
    """Verify /login contains Sign In, Sign Up, and prominent 1-click demo logins."""
    resp = client.get("/login")
    assert resp.status_code == 200
    html = resp.text

    # 1. Tabs
    assert 'id="tabBtnSignIn"' in html
    assert 'id="tabBtnSignUp"' in html
    assert 'id="panelSignIn"' in html
    assert 'id="panelSignUp"' in html

    # 2. Prominent Demo Login Buttons
    assert 'id="btnDemoLoginResident"' in html
    assert "Sign in as Eleanor Vance (Resident)" in html
    assert 'id="btnDemoLoginCaregiver"' in html
    assert "Sign in as David Vance (Caregiver)" in html

    # 3. Form fields and validation containers
    assert 'id="loginEmail"' in html
    assert 'id="loginPassword"' in html
    assert 'id="btnLogin"' in html
    assert 'id="loginErrorMsg"' in html

    assert 'id="signupName"' in html
    assert 'id="signupRole"' in html
    assert 'id="signupEmail"' in html
    assert 'id="signupCaregiver"' in html
    assert 'id="signupPassword"' in html
    assert 'id="signupConfirmPassword"' in html
    assert 'id="btnSignup"' in html
    assert 'id="signupErrorMsg"' in html


def test_index_html_has_all_four_person1_views():
    """Verify index.html contains navigation buttons and panels for all 4 Person 1 views."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # 1. Navigation Buttons
    assert 'id="tabBtnHomeDashboard"' in html
    assert 'id="tabBtnCaregiverDashboard"' in html
    assert 'id="tabBtnElderlyProfile"' in html
    assert 'id="tabBtnMedicationReminders"' in html

    # 2. Content Panels
    assert 'id="panelHomeDashboard"' in html
    assert 'id="panelCaregiverDashboard"' in html
    assert 'id="panelElderlyProfile"' in html
    assert 'id="panelMedicationReminders"' in html

    # 3. Header Auth Integration
    assert 'id="headerActiveUserBadge"' in html
    assert 'id="btnLogout"' in html
    assert "person1_module.js" in html


def test_home_dashboard_elements():
    """Verify Home Dashboard contains welcome greeting, status metrics, and quick actions."""
    resp = client.get("/")
    html = resp.text

    assert 'id="dashWelcomeName"' in html
    assert 'id="dashResidentAge"' in html
    assert 'id="dashResidentRoom"' in html
    assert 'id="dashResidentAddress"' in html

    # Status Cards
    assert 'id="dashCheckinStatusBadge"' in html
    assert 'id="dashCheckinDesc"' in html
    assert 'id="dashMedCount"' in html
    assert 'id="dashMedProgressBar"' in html
    assert 'id="dashNextMed"' in html
    assert 'id="dashIncStatusBadge"' in html
    assert 'id="dashCaregiverName"' in html
    assert 'id="dashCaregiverPhone"' in html

    # Quick Actions & Activity
    assert 'id="dashBtnCheckin"' in html
    assert 'id="dashBtnMeds"' in html
    assert 'id="dashRecentActivityList"' in html


def test_caregiver_dashboard_elements():
    """Verify Caregiver Dashboard contains caregiver persona, status labels, and telemetry."""
    resp = client.get("/")
    html = resp.text

    assert 'id="caregiverResidentStatusBadge"' in html
    assert 'id="caregiverEmergencyAlertCallout"' in html
    assert 'id="cgResidentName"' in html
    assert 'id="cgResidentAge"' in html
    assert 'id="cgResidentAddress"' in html
    assert 'id="cgResidentRoom"' in html
    assert 'id="cgSensorHeartRate"' in html
    assert 'id="cgSensorPosture"' in html
    assert 'id="cgSensorMotion"' in html
    assert 'id="cgCheckinStatus"' in html
    assert 'id="cgMedAdherenceSummary"' in html
    assert 'id="cgMedDoseList"' in html


def test_elderly_profile_elements():
    """Verify Elderly Profile contains resident details, emergency contacts, conditions, and edit form."""
    resp = client.get("/")
    html = resp.text

    # View Mode
    assert 'id="profileResidentName"' in html
    assert 'id="profileResidentAge"' in html
    assert 'id="profileResidentAddress"' in html
    assert 'id="profileDoorPinDisplay"' in html
    assert 'id="profileGuardianDisplay"' in html
    assert 'id="profileGuardianPhoneDisplay"' in html
    assert 'id="profileConditionsList"' in html
    assert 'id="btnEditProfile"' in html
    assert 'id="profileViewContainer"' in html

    # Edit Form
    assert 'id="profileEditContainer"' in html
    assert 'id="editProfileName"' in html
    assert 'id="editProfileAge"' in html
    assert 'id="editProfileAddress"' in html
    assert 'id="editProfileGuardian"' in html
    assert 'id="editProfileGuardianPhone"' in html
    assert 'id="editProfileDoorPin"' in html
    assert 'id="btnSaveProfile"' in html
    assert 'id="btnCancelProfileEdit"' in html
    assert 'id="profileFormError"' in html


def test_medication_reminders_elements():
    """Verify Medication Reminders contains schedule metrics, cards grid, add modal, and history table."""
    resp = client.get("/")
    html = resp.text

    assert 'id="medAdherenceSummary"' in html
    assert 'id="medNextDoseSummary"' in html
    assert 'id="medAdherenceScore"' in html
    assert 'id="demoMedicationsGrid"' in html
    assert 'id="btnAddMedicationModalBtn"' in html

    # Add Modal
    assert 'id="addMedicationModal"' in html
    assert 'id="inputMedName"' in html
    assert 'id="inputMedDosage"' in html
    assert 'id="inputMedTime"' in html
    assert 'id="inputMedPurpose"' in html
    assert 'id="btnSaveNewMedication"' in html
    assert 'id="btnCancelNewMedication"' in html
    assert 'id="addMedErrorMsg"' in html

    # History Table
    assert 'id="demoMedicationHistoryTableBody"' in html


def test_person2_compatibility_preserved():
    """Verify Person 2 views and components are completely preserved."""
    resp = client.get("/")
    html = resp.text

    # All 7 Person 2 tabs remain intact
    assert 'id="tabBtnVoiceAssistant"' in html
    assert 'id="tabBtnDailyCheckin"' in html
    assert 'id="tabBtnFallDetection"' in html
    assert 'id="tabBtnEmergencyAlert"' in html
    assert 'id="tabBtnLocationMap"' in html
    assert 'id="tabBtnNotificationCenter"' in html
    assert 'id="tabBtnIncidentHistory"' in html

    # All 7 Person 2 panels remain intact
    assert 'id="panelVoiceAssistant"' in html
    assert 'id="panelDailyCheckin"' in html
    assert 'id="panelFallDetection"' in html
    assert 'id="panelEmergencyAlert"' in html
    assert 'id="panelLocationMap"' in html
    assert 'id="panelNotificationCenter"' in html
    assert 'id="panelIncidentHistory"' in html