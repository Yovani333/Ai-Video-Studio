$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$frontendPath = Join-Path $repositoryRoot "frontend"

if (-not (Test-Path (Join-Path $frontendPath "node_modules"))) {
    throw "Frontend dependencies not found. Run npm install in the frontend directory first."
}

Set-Location $frontendPath
npm run dev
