"""
FastAPI Application Entry Point for Aegis Ambient Care MCP Server.
Amazon Developer Hackathon 2026.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import init_db
from app.routers import (
    health, tools_http, mcp_server, risk_api, incidents_api,
    events_api, demo_api, live_api, security_api, medications_api, auth_api
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite/PostgreSQL schema and seed default patient profile
    init_db()

    # Warm-up phase to eliminate cold-start latency for Alexa requests
    from app.services.risk_engine import RiskEngine
    from app.models.schemas import Event, Context
    from datetime import datetime, timezone

    # JIT / memory warm-up
    dummy_event = Event(
        event_type="warmup",
        confidence=1.0,
        location="living_room",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    dummy_context = Context(
        activity="idle",
        time_context="afternoon",
        baseline_deviation=0.0,
        wearable_status="worn_normal",
        environment="well_lit"
    )
    _ = RiskEngine.evaluate(dummy_event, dummy_context)

    # State restart-recovery: re-hydrate active emergency state & recent evidence from persistent storage
    from app.database.session import SessionLocal
    from app.services.event_pipeline import global_pipeline
    db = SessionLocal()
    try:
        global_pipeline.recover_state_from_database(db)
    except Exception:
        pass
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Streamable HTTP Model Context Protocol (MCP) Server for Aegis Ambient Care (Alexa+ Integration). "
        "Engineered for the Amazon Developer Hackathon 2026 with hard sub-500ms voice latency guarantees."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ---------------------------------------------------------------------------
# Middleware: CORS Configuration
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=["X-Response-Time-Ms", "X-Process-Time-Ms", "Server-Timing"]
)


# ---------------------------------------------------------------------------
# Middleware: Latency SLA & Server-Timing Tracker
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_latency_timing_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000.0

    # Attach performance telemetry headers
    response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
    response.headers["Server-Timing"] = f"total;dur={process_time_ms:.2f}"

    # Prevent stale browser caching during development and hackathon testing
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


# ---------------------------------------------------------------------------
# Mount Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(events_api.router)
app.include_router(incidents_api.router)
app.include_router(risk_api.router)
app.include_router(tools_http.router)
app.include_router(mcp_server.router)
app.include_router(demo_api.router)
app.include_router(live_api.router)
app.include_router(security_api.router)
app.include_router(medications_api.router)
app.include_router(auth_api.router)


from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import os

# ---------------------------------------------------------------------------
# Mount Static Files & Web Dashboard Frontend (Leela)
# ---------------------------------------------------------------------------
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


from starlette.responses import Response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Satisfy browser favicon queries cleanly without 404 warnings."""
    return Response(status_code=204)


@app.get("/", tags=["Dashboard Frontend"])
@app.get("/dashboard", tags=["Dashboard Frontend"])
async def dashboard():
    """Serves the Aegis Ambient Care Real-Time Safety Dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Dashboard under construction"}


@app.get("/login", tags=["Dashboard Frontend"])
async def login_page():
    """Serves the separate User / Caregiver Login page."""
    login_file = os.path.join(static_dir, "login.html")
    if os.path.exists(login_file):
        return FileResponse(
            login_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Login page not found"}


@app.get("/admin", tags=["Dashboard Frontend"])
async def admin_page():
    """Serves the Family Admin Guardian Console for Eleanor's son and primary guardians."""
    admin_file = os.path.join(static_dir, "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(
            admin_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Admin console not found"}


@app.get("/api/info", tags=["Root"])
async def api_info():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "hackathon": "Amazon Developer Hackathon 2026",
        "description": "Ambient AI safety agent MCP server exposing capabilities to Alexa+",
        "latency_budget": f"{settings.LATENCY_BUDGET_MS}ms",
        "endpoints": {
            "web_dashboard": "/dashboard",
            "mcp_streamable_http": "/mcp",
            "mcp_sse": "/sse",
            "direct_tools": "/tools",
            "interactive_docs": "/docs",
            "health": "/health"
        }
    }
