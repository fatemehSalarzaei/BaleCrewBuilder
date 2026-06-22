import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.main import app
from app.services.approval_service import ApprovalService
from app.services.blueprint_service import BlueprintService
from app.services.document_service import DocumentService
from app.services.project_service import ProjectService
from app.services.validation_service import BlueprintValidationService


@pytest.fixture
def project_service() -> ProjectService:
    return ProjectService()


@pytest.fixture
def document_service() -> DocumentService:
    return DocumentService()


@pytest.fixture
def approval_service(project_service: ProjectService) -> ApprovalService:
    return ApprovalService(project_service=project_service)


@pytest.fixture
def blueprint_service(project_service: ProjectService) -> BlueprintService:
    validation_svc = BlueprintValidationService()
    return BlueprintService(project_service=project_service, validation_service=validation_svc)


@pytest.fixture
async def client(
    project_service: ProjectService,
    document_service: DocumentService,
    approval_service: ApprovalService,
    blueprint_service: BlueprintService,
) -> AsyncClient:
    app.dependency_overrides[deps.get_project_service] = lambda: project_service
    app.dependency_overrides[deps.get_document_service] = lambda: document_service
    app.dependency_overrides[deps.get_approval_service] = lambda: approval_service
    app.dependency_overrides[deps.get_blueprint_service] = lambda: blueprint_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
