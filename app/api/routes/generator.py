from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_generation_service
from app.generator.template_registry import (
    MissingRequiredTemplateError,
    UnknownModuleError,
    UnknownTemplateProfileError,
)
from app.schemas.generation import GenerationRunRead
from app.services.generation_gate_service import GenerationBlockedError
from app.services.generation_service import GenerationService
from app.services.project_service import ProjectNotFoundError

router = APIRouter(prefix="/projects", tags=["generator"])


@router.post(
    "/{project_id}/generate",
    response_model=GenerationRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_generation(
    project_id: UUID,
    generation_svc: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationRunRead:
    try:
        return await generation_svc.run_generation(project_id)
    except GenerationBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)
    except (UnknownTemplateProfileError, UnknownModuleError, MissingRequiredTemplateError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
