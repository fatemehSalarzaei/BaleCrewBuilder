from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from app.ai.blueprint_flow import BlueprintFlow, BlueprintFlowInput
from app.api.deps import (
    get_blueprint_flow_dep,
    get_blueprint_service,
    get_document_service,
    get_project_service,
)
from app.schemas.blueprint import BotBlueprint, BlueprintGenerateResponse, ValidationResultRead
from app.schemas.project import ProjectStatus
from app.services.blueprint_service import (
    BlueprintNotFoundError,
    BlueprintService,
    BlueprintSubmissionNotAllowedError,
    build_placeholder_blueprint,
)
from app.services.document_service import DocumentService
from app.services.project_service import ProjectNotFoundError, ProjectService

router = APIRouter(prefix="/projects", tags=["blueprints"])


async def _require_project(project_id: UUID, svc: ProjectService) -> None:
    try:
        await svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/{project_id}/blueprint",
    response_model=BotBlueprint,
    status_code=status.HTTP_201_CREATED,
)
async def store_blueprint(
    project_id: UUID,
    payload: BotBlueprint,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    blueprint_svc: Annotated[BlueprintService, Depends(get_blueprint_service)],
) -> BotBlueprint:
    await _require_project(project_id, project_svc)
    try:
        return await blueprint_svc.store(project_id, payload)
    except BlueprintSubmissionNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@router.get(
    "/{project_id}/blueprint",
    response_model=BotBlueprint,
)
async def get_blueprint(
    project_id: UUID,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    blueprint_svc: Annotated[BlueprintService, Depends(get_blueprint_service)],
) -> BotBlueprint:
    await _require_project(project_id, project_svc)
    try:
        return await blueprint_svc.get(project_id)
    except BlueprintNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blueprint stored for this project",
        )


@router.post(
    "/{project_id}/blueprint/validate",
    response_model=ValidationResultRead,
    status_code=status.HTTP_200_OK,
)
async def validate_blueprint(
    project_id: UUID,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    blueprint_svc: Annotated[BlueprintService, Depends(get_blueprint_service)],
) -> ValidationResultRead:
    await _require_project(project_id, project_svc)
    try:
        result = await blueprint_svc.validate(project_id)
    except BlueprintNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blueprint stored for this project; submit one first",
        )
    return ValidationResultRead(is_valid=result.is_valid, errors=result.errors)


@router.post(
    "/{project_id}/blueprint/generate",
    response_model=BlueprintGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_blueprint_from_document(
    project_id: UUID,
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    blueprint_svc: Annotated[BlueprintService, Depends(get_blueprint_service)],
    doc_svc: Annotated[DocumentService, Depends(get_document_service)],
    blueprint_flow: Annotated[BlueprintFlow, Depends(get_blueprint_flow_dep)],
    mode: Annotated[Literal["placeholder", "ai"], Query()] = "placeholder",
    additional_context: Annotated[str | None, Query(max_length=2000)] = None,
) -> BlueprintGenerateResponse:
    try:
        project = await project_svc.get(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.status != ProjectStatus.DOCUMENT_APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Blueprint generation requires project status DOCUMENT_APPROVED. "
                f"Current status: {project.status}"
            ),
        )

    latest_doc = await doc_svc.get_latest_for_project(project_id)
    if latest_doc is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No project document found. Create and approve a document "
                "before generating the Blueprint."
            ),
        )

    if mode == "placeholder":
        blueprint = build_placeholder_blueprint(
            project_name=project.name,
            document_title=latest_doc.title,
            document_content=latest_doc.content,
        )
    else:
        flow_input = BlueprintFlowInput(
            project_name=project.name,
            document_title=latest_doc.title,
            document_content=latest_doc.content,
            additional_context=additional_context,
        )
        try:
            proposal = await blueprint_flow.run(flow_input)
            blueprint = BotBlueprint.model_validate(proposal)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"AI Blueprint proposal was invalid: {exc}",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI Blueprint proposal flow failed: {exc}",
            )

    try:
        await blueprint_svc.store(project_id, blueprint)
    except BlueprintSubmissionNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)

    updated_project = await project_svc.get(project_id)

    return BlueprintGenerateResponse(
        blueprint=blueprint,
        source_document_id=latest_doc.id,
        project_status=updated_project.status,
    )
