"""
Unified NIRA Master Application Server.
Amazon Developer Hackathon 2026.

Integrates:
- Caretaker Authentication & Registration Portal (/login)
- Unified Dual Gateway Screen (Demo Mode vs Live Mode) (/)
- Live Ambient AI Safety System (/live)
- Teammates' Demo Showcase (/demo) [Untouched Demo/ folder]
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
DEMO_DIR = ROOT_DIR / "Demo"
LIVE_DIR = ROOT_DIR / "Live"

for p in [str(ROOT_DIR), str(DEMO_DIR), str(LIVE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import Live system
from Live.app.main import app as live_app
from Live.app.static import __file__ as static_marker_file
LIVE_STATIC = Path(static_marker_file).parent

# Import Demo app without modifying any file in Demo/
try:
    from Demo.app.main import app as demo_app
except Exception as e:
    demo_app = None
    print(f"[NIRA] Demo app import note: {e}")

# Master Unified Application
app = FastAPI(
    title="NIRA — Unified Ambient AI Safety Platform",
    description="Amazon Developer Hackathon 2026. Caretaker Portal, Real-Time Ingestion, and Demo Showcase.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Live Static Files
app.mount("/live/static", StaticFiles(directory=str(LIVE_STATIC)), name="live_static_mount")

# Mount Live Application sub-router & endpoints
app.mount("/live-engine", live_app)

# Mount Demo App if available under /demo (Untouched Demo/ folder)
if demo_app is not None:
    app.mount("/demo", demo_app)
    try:
        from Demo.app.routers import (
            health as demo_health,
            incidents_api as demo_incidents,
            events_api as demo_events,
            risk_api as demo_risk,
            demo_api as demo_demo,
            live_api as demo_live
        )
        app.include_router(demo_health.router)
        app.include_router(demo_incidents.router)
        app.include_router(demo_events.router)
        app.include_router(demo_risk.router)
        app.include_router(demo_demo.router)
        app.include_router(demo_live.router)
    except Exception as de:
        print(f"[NIRA] Demo router forward notice: {de}")


# ---------------------------------------------------------------------------
# Core Entry Point Routing
# ---------------------------------------------------------------------------

@app.get("/", summary="NIRA Gateway: Demo Mode vs Live Mode Selector")
def gateway_index():
    """Serves the clean dual gateway screen (Demo Mode vs Live Mode). Redirects to /login if unauthenticated."""
    gateway_file = LIVE_STATIC / "gateway.html"
    if gateway_file.exists():
        return FileResponse(gateway_file)
    return RedirectResponse(url="/login")


@app.get("/login", summary="Caretaker Login & Registration Portal")
def login_portal():
    """Serves the Caretaker Portal with Sign In and full Registration forms."""
    login_file = LIVE_STATIC / "login.html"
    if login_file.exists():
        return FileResponse(login_file)
    return FileResponse(LIVE_STATIC / "gateway.html")


@app.get("/live", summary="Real-Time Ingestion Live System")
def live_console():
    """Serves the complete Live Mode Ambient Safety Dashboard."""
    dash_file = LIVE_STATIC / "live_dashboard.html"
    if dash_file.exists():
        return FileResponse(dash_file)
    return RedirectResponse(url="/")


# Forward Live APIs to live_app routers
for route in live_app.routes:
    if hasattr(route, "path") and (route.path.startswith("/api/v1/live") or route.path.startswith("/live")):
        # Routers already mounted via /live-engine and submounted
        pass

# Also include the routers directly on root app for direct access /api/v1/live/*
from Live.app.routers.auth import router as live_auth_router
from Live.app.routers.location import router as live_location_router
from Live.app.routers.reminders import router as live_reminders_router
from Live.app.routers.heartbeat import router as live_heartbeat_router
from Live.app.routers.emergency import router as live_emergency_router
from Live.app.routers.vision import router as live_vision_router
from Live.api.voice_routes import router as live_voice_router

app.include_router(live_auth_router)
app.include_router(live_location_router)
app.include_router(live_reminders_router)
app.include_router(live_heartbeat_router)
app.include_router(live_emergency_router)
app.include_router(live_vision_router)
app.include_router(live_voice_router)


if __name__ == "__main__":
    import uvicorn
    print("\n==================================================================")
    print(" [NIRA] Starting Master Unified Platform (Live & Demo)")
    print(" Gateway URL: http://localhost:8000/ or http://127.0.0.1:8000/")
    print(" Caretaker Login: http://localhost:8000/login")
    print(" Live Mode:       http://localhost:8000/live")
    print(" Demo Mode:       http://localhost:8000/demo")
    print("==================================================================\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
