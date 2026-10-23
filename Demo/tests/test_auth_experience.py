"""
Authentication Experience Tests — NIRA Ambient Care.

Validates the upgraded /login experience (sign in, sign up, password recovery)
without touching any other surface of the application:

1. The authentication page is served and exposes the complete, accessible
   sign-in / sign-up / recovery interface.
2. The three published demo profiles are preserved byte-for-byte in label,
   role description, icon and post-login destination.
3. The authentication client (auth.js) is served and keeps the legacy global
   contract used by the rest of the application.
4. Security regression guards: no raw password is ever persisted, and demo
   credentials are only ever stored as salted PBKDF2 digests.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def login_html():
    resp = client.get("/login")
    assert resp.status_code == 200
    return resp.text


@pytest.fixture(scope="module")
def auth_js():
    resp = client.get("/static/auth.js")
    assert resp.status_code == 200
    return resp.text


# ---------------------------------------------------------------------------
# 1. Page structure
# ---------------------------------------------------------------------------
def test_login_page_served():
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "NIRA Ambient Care" in resp.text


def test_sign_in_panel_structure(login_html):
    assert 'id="panelSignIn"' in login_html
    assert 'id="loginForm"' in login_html
    assert 'id="loginEmail"' in login_html
    assert 'id="loginPassword"' in login_html
    assert 'id="btnLogin"' in login_html
    assert 'id="loginErrorMsg"' in login_html
    assert 'id="loginSuccessMsg"' in login_html
    assert 'id="btnForgotPassword"' in login_html


def test_sign_up_panel_structure(login_html):
    assert 'id="panelSignUp"' in login_html
    assert 'id="signupForm"' in login_html
    assert 'id="signupName"' in login_html
    assert 'id="signupRole"' in login_html
    assert 'id="signupEmail"' in login_html
    assert 'id="signupCaregiver"' in login_html
    assert 'id="signupPassword"' in login_html
    assert 'id="signupConfirmPassword"' in login_html
    assert 'id="btnSignup"' in login_html
    assert 'id="signupErrorMsg"' in login_html
    assert 'id="signupSuccessMsg"' in login_html


def test_password_strength_and_policy_widgets(login_html):
    assert 'id="signupStrengthMeter"' in login_html
    assert 'id="signupStrengthLabel"' in login_html
    assert 'id="signupPolicyList"' in login_html
    # Sign-up and recovery each render a 4-segment strength meter.
    assert login_html.count('class="strength-meter"') == 2
    assert login_html.count('class="strength-seg"') == 8


def test_password_visibility_toggles(login_html):
    for field in ("loginPassword", "signupPassword", "signupConfirmPassword"):
        assert f'data-password-toggle="{field}"' in login_html
    assert login_html.count('aria-pressed="false"') >= 3


def test_password_recovery_dialog(login_html):
    assert 'id="authRecoveryBackdrop"' in login_html
    assert 'id="recoveryForm"' in login_html
    assert 'id="recoveryEmail"' in login_html
    assert 'id="recoveryNewPassword"' in login_html
    assert 'id="recoveryConfirmPassword"' in login_html
    assert 'id="btnRecoverySubmit"' in login_html
    assert 'id="btnRecoveryReset"' in login_html
    assert 'id="btnRecoveryClose"' in login_html


def test_accessibility_attributes_present(login_html):
    # Tabs expose the tab/tabpanel relationship.
    assert 'role="tablist"' in login_html
    assert 'role="tabpanel"' in login_html
    assert 'aria-controls="panelSignIn"' in login_html
    assert 'aria-controls="panelSignUp"' in login_html
    assert 'aria-labelledby="tabBtnSignIn"' in login_html
    assert 'aria-labelledby="tabBtnSignUp"' in login_html
    # Errors are announced, fields reference their message.
    assert 'role="alert"' in login_html
    assert 'aria-live="polite"' in login_html
    assert 'aria-invalid' in login_html or 'aria-describedby' in login_html
    assert 'aria-describedby="loginEmailError"' in login_html
    assert 'aria-describedby="signupConfirmPasswordError"' in login_html
    # Modal semantics.
    assert 'role="dialog"' in login_html
    assert 'aria-modal="true"' in login_html


def test_password_manager_autocomplete_tokens(login_html):
    assert 'autocomplete="username"' in login_html
    assert 'autocomplete="current-password"' in login_html
    assert 'autocomplete="new-password"' in login_html
    assert 'autocomplete="email"' in login_html
    assert 'autocomplete="name"' in login_html


def test_deployment_mode_disclosure(login_html):
    assert 'id="authModeBanner"' in login_html
    assert 'id="authModeBannerText"' in login_html


# ---------------------------------------------------------------------------
# 2. Demo profiles must remain untouched
# ---------------------------------------------------------------------------
def test_demo_profiles_preserved(login_html):
    assert 'id="btnDemoLoginResident"' in login_html
    assert 'id="btnDemoLoginCaregiver"' in login_html
    assert 'id="btnDemoLoginEMS"' in login_html

    assert "Sign in as Eleanor Vance (Resident)" in login_html
    assert "Sign in as David Vance (Caregiver)" in login_html
    assert "Medic 14 (Boston EMS First Responder)" in login_html

    assert "Home Dashboard &bull; Daily Check-in &bull; Medication Reminders" in login_html
    assert "Caregiver Dashboard &bull; Emergency Alerts &bull; Sensor Matrix" in login_html
    assert "Emergency CAD Telemetry &bull; Smart Door Token: 8492" in login_html

    assert "👵" in login_html
    assert "👨‍💼" in login_html
    assert "🚑" in login_html

    assert "Or 1-Click Demo Profiles" in login_html


def test_demo_profile_destinations_preserved(auth_js):
    assert "redirect: '/#demo/homedashboard'" in auth_js
    assert "redirect: '/#demo/caregiverdashboard'" in auth_js
    assert "redirect: '/#demo/emergencyalert'" in auth_js


# ---------------------------------------------------------------------------
# 3. Authentication client module
# ---------------------------------------------------------------------------
def test_auth_js_served_with_public_api(auth_js):
    assert "global.NiraAuth" in auth_js
    assert "handleLoginSubmit" in auth_js
    assert "handleSignupSubmit" in auth_js
    assert "handleRecoverySubmit" in auth_js
    assert "handleRecoveryReset" in auth_js
    assert "switchAuthTab" in auth_js
    assert "togglePassword" in auth_js
    assert "quickLogin" in auth_js


def test_auth_js_keeps_legacy_globals(auth_js):
    # The previous page exposed these as globals; other surfaces may rely on
    # them, so they must continue to exist.
    for name in (
        "global.switchAuthTab",
        "global.togglePassword",
        "global.quickLogin",
        "global.handleLoginSubmit",
        "global.handleSignupSubmit",
        "global.submitUserSession",
        "global.DEMO_PERSONAS",
    ):
        assert name in auth_js


def test_auth_js_uses_existing_session_contract(auth_js):
    assert "'aegis_auth_user'" in auth_js
    assert "'nira_demo_auth'" in auth_js


def test_auth_js_guards_duplicate_submission(auth_js):
    assert "loginPending" in auth_js
    assert "signupPending" in auth_js
    assert "recoveryPending" in auth_js


def test_auth_js_handles_network_and_server_errors(auth_js):
    assert "AbortController" in auth_js
    assert "describeHttpError" in auth_js
    assert "could not reach the authentication service" in auth_js


# ---------------------------------------------------------------------------
# 4. Security regression guards
# ---------------------------------------------------------------------------
def test_no_raw_password_is_persisted(auth_js):
    """No storage call may ever persist a password value."""
    offenders = re.findall(
        r"(?:localStorage|sessionStorage)\.setItem\([^;]{0,120}?password",
        auth_js,
        re.IGNORECASE,
    )
    assert not offenders, offenders


def test_credentials_are_only_stored_as_digests(auth_js):
    assert "PBKDF2-SHA256" in auth_js
    assert "deriveBits" in auth_js
    assert "importKey" in auth_js
    # The demo credential store only ever receives a digest object.
    assert "credential: credential" in auth_js


def test_no_password_logging(auth_js):
    assert not re.search(r"console\.(log|debug|info|warn)\([^)]*password", auth_js, re.IGNORECASE)


def test_client_does_not_invent_backend_endpoints(auth_js):
    """The client only calls auth paths that the deployment advertises."""
    assert "detectCapabilities" in auth_js
    assert "openapi.json" in auth_js
    assert "paths[AUTH_API.login]" in auth_js


def test_login_page_does_not_embed_server_secrets(login_html):
    for secret_marker in ("API_KEY", "apiKey", "SECRET_KEY", "Bearer ", "client_secret"):
        assert secret_marker not in login_html
