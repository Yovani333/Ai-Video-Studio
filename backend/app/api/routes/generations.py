from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_gpu_provider, get_storage_root
from app.repositories.generation_job_repository import GenerationJobRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.generation import GenerationCreate, GenerationJobRead
from app.services.generation_service import (
    ArtifactUnavailableError,
    GenerationService,
    JobNotFoundError,
    SceneNotFoundError,
)
from app.services.gpu.base import GPUProvider

router = APIRouter(tags=["generation jobs"])
DbSession = Annotated[Session, Depends(get_db)]
Provider = Annotated[GPUProvider, Depends(get_gpu_provider)]
StorageRoot = Annotated[Path, Depends(get_storage_root)]


def _service(
    session: Session, provider: GPUProvider, storage_root: Path
) -> GenerationService:
    return GenerationService(
        GenerationJobRepository(session),
        SceneRepository(session),
        provider,
        storage_root,
    )


@router.post(
    "/projects/{project_id}/scenes/{scene_id}/generations",
    response_model=GenerationJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_generation(
    project_id: str,
    scene_id: str,
    payload: GenerationCreate,
    session: DbSession,
    provider: Provider,
    storage_root: StorageRoot,
) -> GenerationJobRead:
    try:
        return await _service(session, provider, storage_root).create(
            project_id=project_id,
            scene_id=scene_id,
            command=payload,
        )
    except SceneNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc


@router.get("/jobs/{job_id}", response_model=GenerationJobRead)
async def get_generation(
    job_id: str,
    session: DbSession,
    provider: Provider,
    storage_root: StorageRoot,
) -> GenerationJobRead:
    try:
        return await _service(session, provider, storage_root).get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Generation job not found") from exc


@router.post("/jobs/{job_id}/cancel", response_model=GenerationJobRead)
async def cancel_generation(
    job_id: str,
    session: DbSession,
    provider: Provider,
    storage_root: StorageRoot,
) -> GenerationJobRead:
    try:
        return await _service(session, provider, storage_root).cancel(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Generation job not found") from exc


@router.get("/jobs/{job_id}/artifact", response_class=FileResponse)
def get_generation_artifact(
    job_id: str,
    session: DbSession,
    provider: Provider,
    storage_root: StorageRoot,
) -> FileResponse:
    try:
        path, media_type = _service(session, provider, storage_root).artifact_path(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Generation job not found") from exc
    except ArtifactUnavailableError as exc:
        raise HTTPException(status_code=409, detail="Generation artifact is not available") from exc
    return FileResponse(path, media_type=media_type, filename=path.name)
