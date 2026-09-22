$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repositoryRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    throw "Python environment not found. Follow the backend installation steps in README.md."
}

if (-not $env:WORKER_API_TOKEN) {
    throw "Set WORKER_API_TOKEN before starting the diagnostic worker."
}

Set-Location $repositoryRoot
& $pythonPath -m uvicorn worker.app.main:app --reload --host 127.0.0.1 --port 8010
