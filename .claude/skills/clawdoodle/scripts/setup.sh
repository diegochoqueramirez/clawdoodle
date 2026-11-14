#!/usr/bin/env bash
# One-time setup on macOS / Linux (Windows: scripts\setup.ps1 or `python scripts\setup.py`).
set -euo pipefail
exec "${PYTHON:-python3}" "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/setup.py"
