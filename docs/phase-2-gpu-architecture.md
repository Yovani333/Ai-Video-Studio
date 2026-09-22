# Phase 2: Remote GPU architecture

Status: Phase 2A implemented and validated; Phase 2B pending
Decision date: 2026-09-21

## Phase 2A implementation status

Implemented locally:

- persisted `GenerationJob` records and attempt numbering;
- explicit per-scene generation, job status, and cancellation endpoints;
- provider-neutral `GPUProvider` contract and authenticated HTTP implementation;
- version 1 protocol manifest under `contracts/`;
- independent lightweight worker with an SQLite ledger;
- client-defined job IDs and payload-hash conflict detection;
- sequential diagnostic execution;
- restart recovery for interrupted jobs;
- bearer-token authentication;
- checksum-verifiable JSON diagnostic artifacts;
- backend and worker tests with no CUDA or model dependencies.

Validated end to end over HTTP: FastAPI created a project and scene job, submitted the same UUID to the worker, reconciled the terminal status, retrieved the diagnostic artifact, and matched its SHA-256.

Intentional Phase 2A limitations:

- status reconciliation happens when the job API is queried; there is no background scheduler yet;
- the backend provider can fetch artifact bytes, but durable streamed download and atomic local placement belong to Phase 2B;
- diagnostic cancellation is cooperative; supervised termination of GPU inference belongs to Phase 3;
- the worker supports only the diagnostic engine;
- database migrations have not yet been introduced;
- no remote worker, GPU, model weights, or provider account was provisioned.

## Objective

Reach one real, verifiable video clip generated on a remote GPU without adding CUDA, model weights, or heavy inference dependencies to the local development machine.

Phase 2 deliberately starts with one selected scene. It does not automatically submit all project scenes and does not yet assemble a one-minute video.

## Initial recommendation

- Provider: RunPod Pod, started and stopped manually during development.
- Transport: a project-owned HTTP worker running inside the Pod.
- First engine: Wan2.2-TI2V-5B.
- Initial GPU profile: RTX 4090 with 24 GB VRAM; move to a 48 GB profile if the measured workload is not reliable with offloading.
- Concurrency: one generation at a time.
- Coordination: the local backend submits work and polls the worker over HTTPS.
- Result path: download and verify the clip into `storage/clips`; never expose a remote filesystem path as an artifact URL.

This is a starting point for measurement, not a claim that Wan or RunPod will remain the best-quality or lowest-cost option.

## Why this combination

Wan2.2-TI2V-5B supports both text-to-video and image-to-video workflows. Its official project documents a 24 GB single-GPU path using model offloading, dtype conversion, and a CPU-resident T5 component. That gives the project a plausible first experiment on a commonly available GPU while retaining a path to reference-image continuity.

Wan2.2-A14B is postponed because its documented single-GPU path requires substantially more VRAM. LTX remains an important Draft-mode candidate, but the current LTX-2.5 requirements start at 32 GB VRAM, Python 3.12, CUDA 12.7, 32 GB system RAM, and 100 GB disk. Its runtime must therefore remain isolated from the Python 3.11 backend. Model checkpoint licenses must be reviewed per exact revision; the current LTX-2.x community license is not equivalent to Apache 2.0.

RunPod Pods are preferred over Serverless for the first experiment because model loading, VRAM behavior, logs, and failure recovery need to be observable. Vast.ai remains a valid second provider for the same container, but its marketplace price and host characteristics must be evaluated as a complete offer rather than by GPU price alone.

## Target topology

```text
React
  |
  v
FastAPI (local control plane)
  |
  +--> GenerationService
  |      |
  |      +--> GenerationJobRepository --> SQLite
  |      |
  |      +--> GPUProvider / HTTPS client
  |                  |
  |                  v
  |           Remote GPU worker
  |                  |
  |                  +--> VideoEngine
  |                  |      |
  |                  |      +--> WanEngine
  |                  |
  |                  +--> persistent job ledger
  |                  +--> remote artifact directory
  |
  +<-- poll status and stream verified clip
  |
  +--> storage/clips/<project>/<scene>/<attempt>.mp4
```

The public GitHub Pages frontend is separate from this local control-plane design. A functional public application will later require a hosted backend, authentication, durable database, and object storage.

## ADR-001: local control plane, remote inference

The existing FastAPI backend remains the system of record for projects, scenes, and generation attempts. Heavy model code runs only in the remote worker.

The backend initiates outbound HTTPS connections. This avoids requiring a public callback endpoint or a tunnel into the user's local computer. The frontend polls FastAPI; it never communicates with the GPU worker directly.

## ADR-002: provider and engine are separate boundaries

`GPUProvider` owns transport and remote lifecycle operations:

```text
probe
submit
get_status
cancel
download_artifact
```

`VideoEngine` owns inference capabilities and validation inside the worker:

```text
capabilities
validate_request
generate_clip
```

The first provider implementation is an HTTP client configured for a worker running on a RunPod Pod. It should not contain RunPod provisioning or billing calls. The same worker contract can later run on a Vast.ai instance.

CUDA, PyTorch, model repositories, and model weights live under a future top-level `worker/` package and its container. The worker must never be imported by `backend/app`.

## ADR-003: persisted asynchronous jobs

Creating a project must remain inexpensive and compatible: `POST /api/projects` creates the project and scene plan but does not start paid GPU work.

Generation is explicit and initially targets one scene:

```text
POST /api/projects/{project_id}/scenes/{scene_id}/generations
GET  /api/jobs/{job_id}
POST /api/jobs/{job_id}/cancel
GET  /api/scenes/{scene_id}/clip
```

Suggested internal job states:

```text
queued
submitting
running
transferring
succeeded
failed
timed_out
cancelled
```

`submitting` is intentionally distinct: a network timeout does not prove that the remote worker did not receive the job.

A `GenerationJob` should record:

- client-generated job UUID;
- project and scene identifiers;
- prompt revision or immutable prompt snapshot;
- attempt number;
- provider and engine;
- model checkpoint and revision;
- requested and effective generation parameters;
- seed;
- state and timestamps;
- remote job reference;
- GPU type and execution time;
- error category and sanitized message;
- artifact metadata and checksum;
- estimated cost metadata.

## ADR-004: idempotent remote protocol

The backend persists a job before attempting submission and chooses its identifier. Worker API version 1:

```text
GET  /v1/health
GET  /v1/readiness
PUT  /v1/jobs/{job_id}
GET  /v1/jobs/{job_id}
POST /v1/jobs/{job_id}/cancel
GET  /v1/jobs/{job_id}/artifacts/clip
```

Rules:

- The worker stores the job ID and canonical payload hash in a small ledger on persistent storage.
- Repeating the same ID with the same payload returns the original job.
- Reusing an ID with a different payload returns `409 Conflict`.
- After an uncertain submission result, the backend queries and may resubmit only the same ID.
- Deliberate regeneration creates a new job and increments the attempt number.
- The worker claims at most one queued job transactionally.
- A job interrupted by worker restart becomes visibly failed or interrupted; it is not silently rerun.
- Exactly-once execution is not promised after storage loss or a crash during inference.

Timeout and cancellation must terminate a supervised inference process where possible. Cancelling an async Python task alone does not guarantee that CUDA work stops.

## ADR-005: polling first, callbacks later

The backend polls with a configurable interval, exponential backoff, jitter, and a maximum deadline. This works when the backend is behind a home router.

Signed callbacks can later reduce latency after a public backend exists. Polling remains as a reconciliation mechanism even after callbacks are introduced.

## ADR-006: portable, verified artifacts

Remote results contain artifact identifiers and metadata, not paths such as `/workspace/output.mp4`.

Required clip metadata:

- artifact ID;
- MIME type;
- byte length;
- SHA-256;
- width and height;
- FPS and frame count;
- measured duration;
- engine and model revision.

The backend downloads to a `.part` file, streams while hashing, validates length and checksum, and atomically renames the file. A job becomes locally available only after verification succeeds.

Object storage is deferred until the backend becomes public, multiple workers are used, or Serverless is adopted.

## ADR-007: capability-driven generation

Request version 1 should include:

- protocol version;
- job and scene IDs;
- mode (`text_to_video`, later `image_to_video` and frame-conditioned modes);
- engine and model revision;
- prompt;
- desired duration;
- dimensions and FPS;
- seed;
- optional reference artifact IDs.

The engine reports supported modes, dimensions, temporal constraints, and loaded model revision. The backend records requested and effective values because a model may not produce exactly five seconds for every valid frame schedule.

A matching seed does not guarantee identity continuity between scenes. Continuity will require reference-image and frame-conditioned workflows in a later validated phase.

## ADR-008: security and cost controls

- Use HTTPS and a dedicated worker bearer token.
- Keep the worker token separate from provider administrative credentials.
- Never expose secrets through React, `VITE_*`, logs, or API responses.
- Apply allowlists for engines, checkpoints, dimensions, FPS, and generation profiles.
- Reject arbitrary commands, local paths, output paths, and remote URLs from users.
- Limit prompt length, request size, execution time, attempts, and concurrency.
- Sanitize model and infrastructure errors before returning them to the browser.
- Readiness must verify GPU availability and loaded model revision; process health alone is insufficient.
- Set a session budget and an operational reminder to stop the Pod. Stopping inference does not stop Pod billing.
- Track volume charges separately because persistent volumes can continue accruing cost while compute is stopped.

## Incremental delivery plan

### Phase 2A: protocol and lightweight worker

Implement versioned schemas, `GPUProvider`, `GenerationJob`, repositories, sequential worker queue, idempotent endpoints, and a non-video diagnostic engine. The diagnostic engine returns only metadata or a small text artifact; it must not pretend to generate video.

Acceptance criteria:

- repeated identical submission does not create another execution;
- same ID with different payload returns `409`;
- uncertain transport result can be reconciled;
- cancellation and timeout are visible;
- a restart leaves jobs in an explainable state;
- secrets never appear in frontend data;
- all behavior is covered by local tests without GPU dependencies.

### Phase 2B: remote-ready worker

Build a reproducible worker container with authentication, readiness, persistent ledger, artifact streaming, and operational documentation.

Acceptance criteria:

- backend sends a diagnostic job to a remote worker;
- backend polls it to completion;
- a small text artifact is downloaded and checksum-verified;
- no GPU model or secret is installed in the local app;
- provider and worker failures map to stable error categories.

### Phase 3: Wan engine on remote GPU

Pin the Wan source, checkpoint revision, container dependencies, and first inference profile.

Acceptance criteria:

- readiness reports the exact loaded revision;
- one GPU job loads and executes;
- peak VRAM and wall time are recorded;
- out-of-memory and timeout failures are controlled and understandable.

### Phase 4: first real clip

Generate one scene close to five seconds, download it, validate it with `ffprobe`, expose it through FastAPI, and preview it in React.

Acceptance criteria:

- valid MP4 with verified checksum;
- measured frames, FPS, dimensions, and duration stored;
- seed, parameters, GPU, model revision, cold-start time, warm execution time, and estimated cost recorded;
- clip is playable from the scene card;
- no automatic multi-scene generation yet.

## Measurement gate before multiple scenes

Before proceeding to twelve scenes, compare at least:

- prompt adherence;
- motion quality and artifacts;
- effective duration;
- peak VRAM;
- cold and warm generation time;
- successful cost per clip, including failed attempts;
- operational burden;
- suitability for later reference-image continuity.

Only measured results should decide whether to keep Wan, try LTX as Draft mode, change GPU class, or compare Vast.ai.

## Deferred decisions

- automatic Pod provisioning and shutdown;
- RunPod Serverless or Vast Serverless;
- public backend deployment;
- PostgreSQL and migrations;
- object storage;
- callbacks;
- generating all project scenes;
- FFmpeg composition;
- audio and subtitles;
- multi-engine scheduling and automatic fallback.

## Primary references

- [Wan2.2 official repository](https://github.com/Wan-Video/Wan2.2)
- [Wan2.2-TI2V-5B model and license](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B)
- [LTX-Video official repository](https://github.com/Lightricks/LTX-Video)
- [LTX-2 official repository](https://github.com/Lightricks/LTX-2)
- [LTX system requirements](https://docs.ltx.io/open-source-model/getting-started/system-requirements)
- [LTX-2.x license](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x)
- [RunPod pricing](https://www.runpod.io/pricing)
- [RunPod Pod pricing and storage](https://docs.runpod.io/pods/pricing)
- [RunPod asynchronous Serverless jobs](https://docs.runpod.io/serverless/endpoints/send-requests)
- [Vast.ai instance pricing](https://docs.vast.ai/guides/instances/pricing)
- [Vast.ai Serverless overview](https://docs.vast.ai/guides/serverless/overview)
