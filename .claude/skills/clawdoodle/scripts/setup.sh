#!/usr/bin/env bash
# One-time setup for the clawdoodle skill on a new machine: creates engine/.venv with Pillow and checks for Chrome.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
"$PY" -m venv "$HERE/engine/.venv"
"$HERE/engine/.venv/bin/pip" install -q --upgrade pip
"$HERE/engine/.venv/bin/pip" install -q "Pillow>=10"
echo "Pillow: $("$HERE/engine/.venv/bin/python" -c 'import PIL;print(PIL.__version__)')"
"$HERE/engine/.venv/bin/python" - <<PYEOF
import sys; sys.path.insert(0, "$HERE/engine")
import export_gif
print("Chrome:", export_gif.find_chrome())
PYEOF
echo "OK. Use: $HERE/engine/.venv/bin/python $HERE/engine/export_gif.py <scene>"
echo
"$HERE/engine/.venv/bin/python" "$HERE/engine/clawd.py" doctor
