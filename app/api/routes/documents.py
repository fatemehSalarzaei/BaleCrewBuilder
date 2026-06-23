from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.documentation_flow import DocumentationFlow
from app.api.deps import (
    get_ai_run_service,
    get_document_service,
    get_documentation_flow_dep,
    get_project_service,
)
from app.schemas.ai import DocumentationFlowInput
from app.schemas.document import (
    DocumentCreate,
    DocumentGenerateRequest,
    DocumentGenerateResponse,
    DocumentKind,
    DocumentRead,
)
from app.schemas.project import ProjectStatus
from app.services.ai_run_service import AIRunService
from app.services.document_service import DocumentService
from app.services.project_service import (
    IllegalStatusTransitionError,
    ProjectNotFoundError,
    ProjectService,
)

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


@router.post(
    "/{project_id}/documents/generate",
    response_model=DocumentGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_document(
    project_id: UUID,
    payload: DocumentGenerateRequest,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    doc_svc: Annotated[DocumentService, Depends(get_document_service)],
    ai_run_svc: Annotated[AIRunService, Depends(get_ai_run_service)],
    flow: Annotated[DocumentationFlow, Depends(get_documentation_flow_dep)],
) -> DocumentGenerateResponse:
    try:
        project = await project_svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    try:
        await project_svc.transition(project_id, ProjectStatus.DOCUMENT_GENERATING)
    except IllegalStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    flow_input = DocumentationFlowInput(
        project_name=project.name,
        raw_requirements=payload.raw_requirements,
        additional_context=payload.additional_context,
    )

    try:
        run, output = await ai_run_svc.run_documentation_flow(project_id, flow_input, flow)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Documentation flow failed: {exc}",
        )

    title = payload.title or output.title
    doc = await doc_svc.create(
        project_id,
        DocumentCreate(kind=DocumentKind.MARKDOWN, title=title, content=output.content),
    )

    await project_svc.transition(project_id, ProjectStatus.DOCUMENT_DRAFTED)

    return DocumentGenerateResponse(
        document=doc,
        ai_run_id=run.id,
        ai_run_status=run.status,
    )
