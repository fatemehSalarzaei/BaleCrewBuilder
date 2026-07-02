from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status

from app.ai.documentation_flow import DocumentationFlow
from app.api.deps import (
    get_ai_run_service,
    get_document_service,
    get_documentation_flow_dep,
    get_project_service,
    get_text_extraction_service,
    get_upload_service,
)
from app.schemas.ai import DocumentationFlowInput
from app.schemas.document import (
    DocumentCreate,
    DocumentGenerateRequest,
    DocumentGenerateResponse,
    DocumentKind,
    DocumentRead,
    DocumentSubmitReviewResponse,
)
from app.schemas.project import ProjectStatus
from app.schemas.uploaded_file import DocumentUploadResponse, UploadedFileRead
from app.services.ai_run_service import AIRunService
from app.services.document_service import DocumentNotFoundError, DocumentService
from app.services.project_service import (
    IllegalStatusTransitionError,
    ProjectNotFoundError,
    ProjectService,
)
from app.services.text_extraction_service import TextExtractionService, UnsupportedFileTypeError
from app.services.upload_service import UploadService

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


@router.get(
    "/{project_id}/document",
    response_model=DocumentRead,
    status_code=status.HTTP_200_OK,
)
async def get_latest_document(
    project_id: UUID,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    doc_svc: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    try:
        await project_svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    document = await doc_svc.get_latest_for_project(project_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document found for project",
        )
    return document


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
        try:
            await project_svc.transition(
                project_id, ProjectStatus.DOCUMENT_GENERATION_FAILED
            )
        except IllegalStatusTransitionError as transition_exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Documentation flow failed and project status recovery failed: "
                    f"{transition_exc}"
                ),
            )
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


@router.post(
    "/{project_id}/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: UUID,
    file: UploadFile,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    doc_svc: Annotated[DocumentService, Depends(get_document_service)],
    upload_svc: Annotated[UploadService, Depends(get_upload_service)],
    extraction_svc: Annotated[TextExtractionService, Depends(get_text_extraction_service)],
    store_as_document: Annotated[bool, Query()] = True,
    title: Annotated[str | None, Query(max_length=300)] = None,
) -> DocumentUploadResponse:
    try:
        await project_svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    content = await file.read()
    filename = file.filename or "upload"

    try:
        extracted_text = extraction_svc.extract(filename, content)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    uploaded = await upload_svc.store_metadata(
        project_id=project_id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
    )

    document: DocumentRead | None = None
    if store_as_document:
        ext = Path(filename).suffix.lower()
        kind = DocumentKind.MARKDOWN if ext in {".md", ".markdown"} else DocumentKind.RAW_TEXT
        doc_title = title or Path(filename).stem
        document = await doc_svc.create(
            project_id,
            DocumentCreate(kind=kind, title=doc_title, content=extracted_text),
        )

    return DocumentUploadResponse(
        uploaded_file=uploaded,
        extracted_text=extracted_text,
        document=document,
    )


@router.post(
    "/{project_id}/documents/{document_id}/submit-review",
    response_model=DocumentSubmitReviewResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_for_review(
    project_id: UUID,
    document_id: UUID,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    doc_svc: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentSubmitReviewResponse:
    try:
        await project_svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        await doc_svc.get(document_id, project_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        updated = await project_svc.transition(project_id, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    except IllegalStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return DocumentSubmitReviewResponse(
        document_id=document_id,
        project_id=project_id,
        project_status=updated.status,
    )
