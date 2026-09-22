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

The proposed provider-neutral worker design is documented in [docs/phase-2-gpu-architecture.md](docs/phase-2-gpu-architecture.md). No GPU resources or model weights are provisioned by the current repository.

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

cd ..\frontend
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
```

## Environment and secrets

Copy each `.env.example` to `.env` locally. Never commit real GPU credentials. The backend example reserves `GPU_PROVIDER`, `GPU_API_URL`, `GPU_API_KEY`, and `VIDEO_ENGINE` for a later phase.

## Pending phases

- AI-assisted scene prompts and continuity refinement.
- A real remote-GPU `VideoEngine` adapter (Wan, LTX-Video, or another selected engine).
- Job queue, progress reporting, cancellation, retry, and authentication.
- FFmpeg renderer for resolution/FPS normalization, concatenation, audio, and final MP4 output.
- Thumbnails, previews, scene editing, and regeneration.
- Database migrations and PostgreSQL deployment configuration.
