"""
Pytest configuration and environment fixtures for Aegis Ambient Care.
Amazon Developer Hackathon 2026.
"""

import sys
import types
from pathlib import Path

# Ensure project root is always in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure demo namespace maps to PROJECT_ROOT for demo.* imports
if "demo" not in sys.modules:
    _demo_mod = types.ModuleType("demo")
    _demo_mod.__path__ = [str(PROJECT_ROOT)]
    sys.modules["demo"] = _demo_mod
