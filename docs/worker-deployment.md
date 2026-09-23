# Diagnostic worker deployment

This guide deploys the lightweight Phase 2B diagnostic worker. It does not contain
CUDA, PyTorch, model weights, FFmpeg processing, or real video generation.

## Security boundary

- Expose the worker only through HTTPS in a real remote environment.
- Generate a dedicated, long random `WORKER_API_TOKEN`; do not reuse a provider API key.
- Put the token in the hosting platform's secret manager or environment settings.
- Never put the token in `VITE_*`, browser code, an image, a Git commit, or a command log.
- Persist `/data`; it contains the worker job ledger and artifacts.
- Limit inbound access to the backend host when the provider supports firewall rules.

## Build the image

From the repository root:

```powershell
docker build -f .\worker\Dockerfile -t ai-video-studio-worker:phase-2b .
```

The image runs as an unprivileged user and has a health check on `/v1/health`.
Startup fails when `WORKER_API_TOKEN` is missing.

## Validate locally with Docker Compose

Copy the root environment template and replace the token:

```powershell
Copy-Item .env.example .env
docker compose --profile worker up --build worker
```

In another terminal, use the same token without printing it:

```powershell
$headers = @{ Authorization = "Bearer $env:WORKER_API_TOKEN" }
Invoke-RestMethod http://127.0.0.1:8010/v1/readiness -Headers $headers
```

The expected response reports protocol `1`, engine `diagnostic`, and
`accepts_jobs: true`.

The repository also includes a complete protocol smoke test. It creates one
small diagnostic job and validates the downloaded artifact without printing the
token:

```powershell
$env:WORKER_API_TOKEN = "your-worker-token"
.\scripts\test-remote-worker.ps1 -WorkerUrl "https://your-worker-host.example"
```

For a local worker only, pass `-AllowHttp`.

## Deploy on a remote container host

The same image can run on a manually managed GPU Pod or another Docker host even
though the diagnostic engine does not use its GPU. Configure:

```text
WORKER_API_TOKEN=<secret>
WORKER_DATABASE_PATH=/data/worker.db
WORKER_ARTIFACT_ROOT=/data/artifacts
```

Mount durable storage at `/data`, publish container port `8010` behind the
provider's HTTPS endpoint or a TLS reverse proxy, and confirm both health and
authenticated readiness before submitting work.

On the backend, set:

```dotenv
GPU_API_URL=https://your-worker-host.example
GPU_WORKER_TOKEN=the-same-dedicated-worker-token
GPU_REQUEST_TIMEOUT_SECONDS=10
GPU_MAX_ARTIFACT_BYTES=2147483648
VIDEO_ENGINE=diagnostic
```

Restart FastAPI after changing its environment. The browser never receives these
values; FastAPI is the only component that communicates with the worker.

## Verification sequence

1. `GET /v1/health` proves the process answers.
2. Authenticated `GET /v1/readiness` proves the queue consumer is running.
3. Create a project and submit one scene generation through FastAPI.
4. Poll `GET /api/jobs/{job_id}` until it reaches `succeeded`.
5. Confirm `artifact.local_path` is under `storage/clips`.
6. Download `GET /api/jobs/{job_id}/artifact` and compare it with the diagnostic
   metadata.

FastAPI streams remote bytes to a `.part` file, enforces the configured byte
limit, checks the declared byte length and SHA-256, and atomically renames the
file only after validation succeeds. Failed or interrupted transfers do not
publish a final artifact.

## Operations

- Stop or delete paid compute manually after the test; this repository does not
  call provider billing or lifecycle APIs.
- Keep `/data` while reconciliation is needed. Removing it discards the worker's
  idempotency ledger and remote diagnostic artifacts.
- Rotate the worker token after accidental exposure and update FastAPI at the
  same time.
- Inspect sanitized job errors through FastAPI. Do not return infrastructure
  credentials or raw provider logs to the frontend.

## Not included yet

- a Wan, LTX, or other video model;
- provider provisioning and automatic shutdown;
- supervised GPU inference cancellation;
- background polling in FastAPI;
- public backend hosting or object storage.

GitHub Actions runs the backend and worker test suites, builds the frontend, and
builds the diagnostic worker image on every push to `main`. It validates the
container but does not publish an image or create remote infrastructure.
