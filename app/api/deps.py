from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.documentation_flow import DocumentationFlow, get_documentation_flow
from app.db.session import get_db
from app.services.ai_run_service import AIRunService
from app.services.approval_service import ApprovalService
from app.services.blueprint_service import BlueprintService
from app.services.document_service import DocumentService
from app.services.generation_gate_service import GenerationGateService
from app.services.generation_service import GenerationService
from app.services.project_service import ProjectService
from app.services.project_status_service import ProjectStatusService
from app.services.text_extraction_service import TextExtractionService
from app.services.upload_service import UploadService
from app.services.validation_service import BlueprintValidationService


def get_project_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectService:
    return ProjectService(db=db)


def get_document_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentService:
    return DocumentService(db=db)


def get_approval_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalService:
    return ApprovalService(db=db)


def get_blueprint_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BlueprintService:
    return BlueprintService(db=db, validation_service=BlueprintValidationService())


def get_validation_service() -> BlueprintValidationService:
    return BlueprintValidationService()


def get_generation_gate_service(
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
    blueprint_svc: Annotated[BlueprintService, Depends(get_blueprint_service)],
) -> GenerationGateService:
    return GenerationGateService(project_service=project_svc, blueprint_service=blueprint_svc)


def get_project_status_service(
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectStatusService:
    return ProjectStatusService(project_service=project_svc)


def get_generation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    gate: Annotated[GenerationGateService, Depends(get_generation_gate_service)],
    blueprint_svc: Annotated[BlueprintService, Depends(get_blueprint_service)],
) -> GenerationService:
    return GenerationService(db=db, gate=gate, blueprint_svc=blueprint_svc)


def get_ai_run_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIRunService:
    return AIRunService(db=db)


def get_documentation_flow_dep() -> DocumentationFlow:
    return get_documentation_flow()


def get_upload_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UploadService:
    return UploadService(db=db)


def get_text_extraction_service() -> TextExtractionService:
    return TextExtractionService()
