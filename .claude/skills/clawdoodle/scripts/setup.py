#!/usr/bin/env python3
"""One-time setup (macOS, Linux, Windows): creates engine/.venv with Pillow, finds Chrome and runs `clawd doctor`."""
import subprocess, sys, venv
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
VENV = HERE / "engine" / ".venv"
if sys.version_info < (3, 9):
    sys.exit("Python 3.9+ is required.")
venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
PY = next(p for p in (VENV / "bin" / "python", VENV / "Scripts" / "python.exe") if p.exists())
subprocess.check_call([str(PY), "-m", "pip", "install", "-q", "--upgrade", "pip"])
subprocess.check_call([str(PY), "-m", "pip", "install", "-q", "Pillow>=10"])
sys.exit(subprocess.call([str(PY), str(HERE / "engine" / "clawd.py"), "doctor"]))
