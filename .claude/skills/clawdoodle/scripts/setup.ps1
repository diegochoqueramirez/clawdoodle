# One-time setup on Windows (PowerShell). Needs Python 3.9+ (python.org or `py`) and Google Chrome.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $py (Join-Path $here "setup.py")
