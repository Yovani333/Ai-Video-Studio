param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$WorkerUrl,

    [ValidateRange(10, 1800)]
    [int]$TimeoutSeconds = 120,

    [switch]$AllowHttp
)

$ErrorActionPreference = "Stop"

if (-not $env:WORKER_API_TOKEN) {
    throw "Set WORKER_API_TOKEN in this PowerShell session before running the check."
}

$workerUri = [Uri]$WorkerUrl
if ($workerUri.Scheme -ne "https" -and -not $AllowHttp) {
    throw "Remote verification requires HTTPS. Use -AllowHttp only for a trusted local test."
}
if ($workerUri.Scheme -notin @("http", "https")) {
    throw "WorkerUrl must use HTTP or HTTPS."
}

$baseUrl = $WorkerUrl.TrimEnd("/")
$headers = @{ Authorization = "Bearer $env:WORKER_API_TOKEN" }
$readiness = Invoke-RestMethod `
    -Method Get `
    -Uri "$baseUrl/v1/readiness" `
    -Headers $headers `
    -TimeoutSec 15

if ($readiness.status -ne "ready" -or -not $readiness.accepts_jobs) {
    throw "The worker is reachable but is not ready to accept jobs."
}
if ($readiness.protocol_version -ne "1" -or $readiness.engine -ne "diagnostic") {
    throw "The worker protocol or engine does not match the Phase 2B diagnostic contract."
}

$jobId = [Guid]::NewGuid().ToString()
$sceneId = [Guid]::NewGuid().ToString()
$payload = [ordered]@{
    protocol_version       = "1"
    job_id                 = $jobId
    scene_id               = $sceneId
    mode                   = "text_to_video"
    engine                 = "diagnostic"
    model_revision         = "diagnostic-v1"
    prompt                 = "Phase 2B remote diagnostic verification"
    duration_seconds       = 5
    width                  = 1280
    height                 = 704
    fps                    = 24
    seed                   = 7
    reference_artifact_ids = @()
}

$null = Invoke-RestMethod `
    -Method Put `
    -Uri "$baseUrl/v1/jobs/$jobId" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json -Depth 4) `
    -TimeoutSec 30

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 1
    $job = Invoke-RestMethod `
        -Method Get `
        -Uri "$baseUrl/v1/jobs/$jobId" `
        -Headers $headers `
        -TimeoutSec 15
    if ($job.status -in @("failed", "timed_out", "cancelled")) {
        throw "Diagnostic job ended with status '$($job.status)' and code '$($job.error_code)'."
    }
} while ($job.status -ne "succeeded" -and [DateTime]::UtcNow -lt $deadline)

if ($job.status -ne "succeeded" -or -not $job.artifact) {
    throw "Diagnostic job did not complete within $TimeoutSeconds seconds."
}

$temporaryPath = Join-Path ([IO.Path]::GetTempPath()) "$jobId.json"
try {
    Invoke-WebRequest `
        -Method Get `
        -Uri "$baseUrl/v1/jobs/$jobId/artifacts/clip" `
        -Headers $headers `
        -OutFile $temporaryPath `
        -TimeoutSec 60

    $actualLength = (Get-Item -LiteralPath $temporaryPath).Length
    $actualHash = (Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualLength -ne $job.artifact.size_bytes) {
        throw "Artifact length mismatch: expected $($job.artifact.size_bytes), got $actualLength."
    }
    if ($actualHash -ne $job.artifact.sha256) {
        throw "Artifact SHA-256 mismatch."
    }

    [pscustomobject]@{
        Status          = "verified"
        Worker          = $workerUri.Host
        ProtocolVersion = $readiness.protocol_version
        Engine          = $readiness.engine
        JobId           = $jobId
        ArtifactBytes   = $actualLength
        Sha256          = $actualHash
    }
}
finally {
    Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
}
