from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_generation_run_service
from app.schemas.generation import GenerationRunRead
from app.services.generation_run_service import GenerationRunService
from app.services.project_service import ProjectNotFoundError

router = APIRouter(prefix="/projects", tags=["generation-runs"])


@router.get("/{project_id}/runs", response_model=list[GenerationRunRead])
async def list_generation_runs(
    project_id: UUID,
    run_svc: Annotated[GenerationRunService, Depends(get_generation_run_service)],
) -> list[GenerationRunRead]:
    try:
        return await run_svc.list_for_project(project_id)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
