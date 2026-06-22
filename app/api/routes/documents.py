from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_document_service, get_project_service
from app.schemas.document import DocumentCreate, DocumentRead
from app.services.document_service import DocumentService
from app.services.project_service import ProjectNotFoundError, ProjectService

router = APIRouter(prefix="/projects", tags=["documents"])


@router.post(
    "/{project_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    project_id: UUID,
    payload: DocumentCreate,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    doc_svc: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    try:
        await project_svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return await doc_svc.create(project_id, payload)
