from typing import Annotated

from fastapi import Depends

from app.services.approval_service import ApprovalService
from app.services.blueprint_service import BlueprintService
from app.services.document_service import DocumentService
from app.services.generation_gate_service import GenerationGateService
from app.services.project_service import ProjectService
from app.services.project_status_service import ProjectStatusService
from app.services.validation_service import BlueprintValidationService

_project_service = ProjectService()
_document_service = DocumentService()
_approval_service = ApprovalService(project_service=_project_service)
_validation_service = BlueprintValidationService()
_blueprint_service = BlueprintService(
    project_service=_project_service,
    validation_service=_validation_service,
)


def get_project_service() -> ProjectService:
    return _project_service


def get_document_service() -> DocumentService:
    return _document_service


def get_approval_service() -> ApprovalService:
    return _approval_service


def get_validation_service() -> BlueprintValidationService:
    return _validation_service


def get_blueprint_service() -> BlueprintService:
    return _blueprint_service


def get_generation_gate_service(
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
) -> GenerationGateService:
    return GenerationGateService(project_service=project_svc)


def get_project_status_service(
    project_svc: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectStatusService:
    return ProjectStatusService(project_service=project_svc)
