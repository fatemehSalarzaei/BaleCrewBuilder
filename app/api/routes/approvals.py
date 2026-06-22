from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_approval_service, get_project_service
from app.schemas.approval import DocumentApproveCreate, DocumentFeedbackCreate, ReviewRead
from app.services.approval_service import ApprovalService, InvalidDecisionForStatusError
from app.services.project_service import ProjectNotFoundError, ProjectService

router = APIRouter(prefix="/projects", tags=["approvals"])


async def _require_project(project_id: UUID, svc: ProjectService) -> None:
    try:
        await svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/{project_id}/document/approve",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def approve_document(
    project_id: UUID,
    payload: DocumentApproveCreate,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    approval_svc: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ReviewRead:
    await _require_project(project_id, project_svc)
    try:
        return await approval_svc.approve(project_id, payload)
    except InvalidDecisionForStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/{project_id}/document/feedback",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_document_feedback(
    project_id: UUID,
    payload: DocumentFeedbackCreate,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    approval_svc: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ReviewRead:
    await _require_project(project_id, project_svc)
    try:
        return await approval_svc.submit_feedback(project_id, payload)
    except InvalidDecisionForStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/{project_id}/reviews",
    response_model=list[ReviewRead],
)
async def list_reviews(
    project_id: UUID,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    approval_svc: Annotated[ApprovalService, Depends(get_approval_service)],
) -> list[ReviewRead]:
    await _require_project(project_id, project_svc)
    return await approval_svc.list_for_project(project_id)
