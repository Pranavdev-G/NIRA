"""
Bridge module so `uvicorn app:app` or `from app.main import app` resolves directly.
"""
import sys
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_APP = os.path.join(ROOT_DIR, "Demo")
if DEMO_APP not in sys.path:
    sys.path.insert(0, DEMO_APP)

from Demo.app.main import app

# Expose app object directly
main = sys.modules[__name__]
