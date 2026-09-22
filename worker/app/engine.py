import asyncio
import hashlib
import json
from pathlib import Path

from worker.app.schemas import ArtifactMetadata


class DiagnosticEngine:
    """Validates worker orchestration without creating fake media."""

    name = "diagnostic"

    def __init__(self, artifact_root: Path, delay_seconds: float = 0) -> None:
        self.artifact_root = artifact_root
        self.delay_seconds = delay_seconds

    async def generate(self, payload: dict) -> tuple[ArtifactMetadata, dict[str, object]]:
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        job_id = str(payload["job_id"])
        path = self.artifact_root / f"{job_id}.json"
        diagnostic = {
            "protocol_version": "1",
            "job_id": job_id,
            "scene_id": payload["scene_id"],
            "engine": self.name,
            "prompt_sha256": hashlib.sha256(payload["prompt"].encode("utf-8")).hexdigest(),
            "message": "Diagnostic worker completed without video generation.",
        }
        content = json.dumps(diagnostic, sort_keys=True, indent=2).encode("utf-8")
        path.write_bytes(content)
        artifact = ArtifactMetadata(
            artifact_id=f"diagnostic:{job_id}",
            media_type="application/json",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            kind="diagnostic",
            filename=path.name,
        )
        effective = {
            "engine": self.name,
            "video_generated": False,
            "requested_duration_seconds": payload["duration_seconds"],
        }
        return artifact, effective
