from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_gpu_provider
from app.repositories.generation_job_repository import GenerationJobRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.generation import GenerationCreate, GenerationJobRead
from app.services.generation_service import (
    GenerationService,
    JobNotFoundError,
    SceneNotFoundError,
)
from app.services.gpu.base import GPUProvider

router = APIRouter(tags=["generation jobs"])
DbSession = Annotated[Session, Depends(get_db)]
Provider = Annotated[GPUProvider, Depends(get_gpu_provider)]


def _service(session: Session, provider: GPUProvider) -> GenerationService:
    return GenerationService(
        GenerationJobRepository(session),
        SceneRepository(session),
        provider,
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
) -> GenerationJobRead:
    try:
        return await _service(session, provider).create(
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
) -> GenerationJobRead:
    try:
        return await _service(session, provider).get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Generation job not found") from exc


@router.post("/jobs/{job_id}/cancel", response_model=GenerationJobRead)
async def cancel_generation(
    job_id: str,
    session: DbSession,
    provider: Provider,
) -> GenerationJobRead:
    try:
        return await _service(session, provider).cancel(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Generation job not found") from exc
