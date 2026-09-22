$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repositoryRoot "backend"
$pythonPath = Join-Path $backendPath ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    throw "Backend virtual environment not found. Follow the installation steps in README.md."
}

Set-Location $backendPath
& $pythonPath -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
