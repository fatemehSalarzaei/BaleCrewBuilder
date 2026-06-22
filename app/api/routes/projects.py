from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_project_service
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.project_service import ProjectNotFoundError, ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    svc: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectRead:
    return svc.create(payload)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID,
    svc: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectRead:
    try:
        return svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
