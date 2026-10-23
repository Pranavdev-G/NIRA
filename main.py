"""
Unified NIRA Master Application Server.
Amazon Developer Hackathon 2026.

Integrates:
- Demo folder systems & routes (/api/v1/demo/*)
- Live folder systems & routes (/api/v1/live/*)
- Unified Landing Gateway and Dashboard frontend
"""

import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.join(ROOT_DIR, "Demo")
LIVE_DIR = os.path.join(ROOT_DIR, "Live")

for p in [ROOT_DIR, DEMO_DIR, LIVE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import the core FastAPI application from Demo/app/main.py
from Demo.app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    print("\n==================================================================")
    print(" [NIRA] Starting Unified Dashboard (Demo & Live Model)")
    print(" Gateway: http://localhost:8000/ or http://127.0.0.1:8000/")
    print(" [ DEMO ]       -> Calls Demo/ folder routes")
    print(" [ LIVE MODEL ] -> Calls Live/ folder routes")
    print("==================================================================\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
