# Architecture

The HTTP layer validates requests and delegates use cases to application services. Services depend on repositories instead of SQLite directly. SQLAlchemy owns persistence mappings, which keeps a future PostgreSQL migration localized to configuration and migrations.

```text
React UI -> FastAPI routes -> ProjectService -> ProjectRepository -> SQLite
                                |
                                +-> ScenePlanner

Future generation pipeline:
Project -> ScenePlanner -> VideoEngine adapter -> generated clips -> VideoRenderer/FFmpeg -> final MP4
```

`VideoEngine` is provider-neutral. Future adapters such as `WanEngine` or `LTXEngine` can execute against a remote GPU without leaking provider details into routes or project persistence. `VideoRenderer` similarly isolates FFmpeg commands from business logic.

Scene continuity data lives in a structured `SceneContext` containing character, environment, style, lighting, camera, colors, reference images, and seed fields. These fields are intentionally empty during phase 1.

The remote execution architecture, implemented Phase 2A boundaries, and incremental validation plan are documented in [Phase 2: Remote GPU architecture](phase-2-gpu-architecture.md).
