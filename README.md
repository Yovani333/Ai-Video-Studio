# AI Video Studio

Base web architecture for turning a written idea into a one-minute, scene-based AI video. Phase 1 provides project persistence, deterministic scene planning, and a modern web interface. It does **not** install or run video models, CUDA, GPU frameworks, audio generation, or remote GPU providers.

**Frontend preview:** `https://yovani333.github.io/Ai-Video-Studio/`

The GitHub Pages preview hosts only the static React interface. Project creation requires the FastAPI backend to be running locally until a public backend is deployed in a later phase.

## Architecture

- **Backend:** Python 3.11, FastAPI, Pydantic, SQLAlchemy, and SQLite.
- **Frontend:** React, TypeScript, Vite, and Tailwind CSS.
- **Storage:** local folders for project artifacts, temporary clips, and final videos; generated files are ignored by Git.
- **Future integrations:** provider-neutral `VideoEngine`, scene continuity data, and an abstract `VideoRenderer` intended for FFmpeg.

See [docs/architecture.md](docs/architecture.md) for the dependency flow and extension points.

The provider-neutral worker design is documented in [docs/phase-2-gpu-architecture.md](docs/phase-2-gpu-architecture.md). The hardened diagnostic-container procedure is in [docs/worker-deployment.md](docs/worker-deployment.md). No GPU resources or model weights are provisioned by the current repository.

## Requirements

- Python 3.11
- Node.js 20 or newer and npm
- Git
- FFmpeg will be required for final rendering in a later phase; it is not used in phase 1.
- Docker Desktop is optional.

## Backend setup (Windows PowerShell)

From the repository root:

```powershell
cd .\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`. The SQLite database is created automatically.

After setup, the helper can start it from the repository root:

```powershell
.\scripts\start-backend.ps1
```

## Diagnostic worker (Phase 2A/2B)

The lightweight worker validates remote-job behavior without CUDA, model weights, or video generation. In a third PowerShell window:

```powershell
cd C:\path\to\Ai-Video-Studio
$env:WORKER_API_TOKEN = "choose-a-long-local-development-token"
.\backend\.venv\Scripts\python.exe -m uvicorn worker.app.main:app --reload --host 127.0.0.1 --port 8010
```

Configure `backend/.env` with the same token:

```dotenv
GPU_API_URL=http://127.0.0.1:8010
GPU_WORKER_TOKEN=choose-a-long-local-development-token
VIDEO_ENGINE=diagnostic
```

The worker produces a checksum-verifiable JSON diagnostic artifact. It never produces a fake video.
FastAPI streams the artifact into `storage/clips`, validates its declared length and SHA-256, then publishes it atomically. `GPU_MAX_ARTIFACT_BYTES` limits accepted artifact size.

After deploying the diagnostic worker, validate its protocol and artifact independently:

```powershell
$env:WORKER_API_TOKEN = "your-worker-token"
.\scripts\test-remote-worker.ps1 -WorkerUrl "https://your-worker-host.example"
```

## Frontend setup (Windows PowerShell)

Open a second PowerShell window at the repository root:

```powershell
cd .\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://127.0.0.1:5173`. After setup, you can also use:

```powershell
.\scripts\start-frontend.ps1
```

`VITE_API_BASE_URL` controls the frontend API location. `CORS_ORIGINS` in `backend/.env` is a comma-separated allowlist for browser origins.

## API

- `GET /api/health` — service health.
- `POST /api/projects` — create and persist a project and its initial scene plan.
- `GET /api/projects` — list projects, newest first.
- `GET /api/projects/{project_id}` — retrieve a project and scenes.
- `POST /api/projects/{project_id}/scenes/{scene_id}/generations` — explicitly create one generation attempt.
- `GET /api/jobs/{job_id}` — reconcile a job with the configured worker.
- `POST /api/jobs/{job_id}/cancel` — request cancellation.
- `GET /api/jobs/{job_id}/artifact` — download a locally verified artifact.

Example request:

```json
{
  "prompt": "An astronaut explores an unknown planet",
  "duration_seconds": 60,
  "quality": "draft"
}
```

A 60-second project initially receives twelve five-second scenes in `waiting` status. Project states are `created`, `planning`, `queued`, `generating`, `rendering`, `completed`, and `failed`.

## Tests and validation

```powershell
cd .\backend
.\.venv\Scripts\python.exe -m pytest

cd ..
.\backend\.venv\Scripts\python.exe -m pytest worker\tests

cd .\frontend
npm run build
```

## Folder structure

```text
backend/
  app/
    api/             # FastAPI routes and dependencies
    core/            # Settings and database bootstrap
    models/          # SQLAlchemy persistence models
    repositories/    # Replaceable persistence access
    schemas/         # Pydantic API and context contracts
    services/        # Project, planning, engine, and renderer boundaries
    main.py
  tests/
contracts/           # Versioned backend/worker protocol manifest
frontend/
  src/
    api/             # Typed backend client
    components/      # Studio form and project timeline
docs/
scripts/
storage/
  projects/
  clips/
  final/
worker/              # Lightweight remote-ready worker; no GPU model in Phase 2B
```

## Environment and secrets

Copy each `.env.example` to `.env` locally. Never commit real GPU credentials. `GPU_API_URL` and `GPU_WORKER_TOKEN` connect FastAPI to the worker. Provider administrative credentials remain separate and are not used by Phase 2A.

## Pending phases

- AI-assisted scene prompts and continuity refinement.
- Remote validation of the diagnostic worker using a user-controlled endpoint and secret.
- A real remote-GPU `VideoEngine` adapter (Wan, LTX-Video, or another selected engine).
- Supervised inference cancellation, retry policy, and progress reporting.
- FFmpeg renderer for resolution/FPS normalization, concatenation, audio, and final MP4 output.
- Thumbnails, previews, scene editing, and regeneration.
- Database migrations and PostgreSQL deployment configuration.
