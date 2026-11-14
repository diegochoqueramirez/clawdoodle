#!/usr/bin/env python3
"""Cross-platform launcher for the clawdoodle CLI (macOS, Linux, Windows).

Usage: python scripts/run.py <clawd command> [args]      e.g.  python scripts/run.py render my-topic --final
Runs engine/clawd.py with the Python of engine/.venv (bin/python or Scripts/python.exe).
"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
VENV = HERE / "engine" / ".venv"
PY = next((p for p in (VENV / "bin" / "python", VENV / "Scripts" / "python.exe") if p.exists()), None)
if PY is None:
    sys.exit("engine/.venv not found. Run first:  python scripts/setup.py")
sys.exit(subprocess.call([str(PY), str(HERE / "engine" / "clawd.py"), *sys.argv[1:]]))
