from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401 — registers all ORM models with Base.metadata
from app.api import deps
from app.db.base import Base
from app.main import app
from app.services.approval_service import ApprovalService
from app.services.blueprint_service import BlueprintService
from app.services.document_service import DocumentService
from app.services.generation_gate_service import GenerationGateService
from app.services.generation_service import GenerationService
from app.services.project_service import ProjectService
from app.services.validation_service import BlueprintValidationService

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        _TEST_DB_URL,
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def project_service(db: AsyncSession) -> ProjectService:
    return ProjectService(db=db)


@pytest.fixture
def document_service(db: AsyncSession) -> DocumentService:
    return DocumentService(db=db)


@pytest.fixture
def approval_service(db: AsyncSession) -> ApprovalService:
    return ApprovalService(db=db)


@pytest.fixture
def blueprint_service(db: AsyncSession) -> BlueprintService:
    return BlueprintService(db=db, validation_service=BlueprintValidationService())


@pytest.fixture
async def client(db: AsyncSession, tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    gen_output = tmp_path / "generated"
    gen_output.mkdir()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    def _override_get_generation_service() -> GenerationService:
        blueprint_svc = BlueprintService(db=db, validation_service=BlueprintValidationService())
        project_svc = ProjectService(db=db)
        gate = GenerationGateService(project_service=project_svc, blueprint_service=blueprint_svc)
        return GenerationService(db=db, gate=gate, blueprint_svc=blueprint_svc, output_dir=gen_output)

    app.dependency_overrides[deps.get_db] = _override_get_db
    app.dependency_overrides[deps.get_generation_service] = _override_get_generation_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
