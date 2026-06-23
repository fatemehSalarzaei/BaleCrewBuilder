"""Tests for Phase 2: CrewAI Documentation Flow Abstraction.

All tests use the fallback or mocked flows — no real LLM or API keys required.
"""
import ast
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.documentation_flow import DocumentationFlow, get_documentation_flow
from app.ai.fallback_documentation_flow import FallbackDocumentationFlow
from app.schemas.ai import AIRunStatus, DocumentationFlowInput, DocumentationFlowOutput
from app.services.ai_run_service import AIRunService

_AI_PACKAGE = Path(__file__).parent.parent / "app" / "ai"


# ── Local fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
async def project_id(db: AsyncSession) -> UUID:
    from app.db.models.projects import ProjectModel
    from app.schemas.project import ProjectStatus

    pid = uuid4()
    now = datetime.now(timezone.utc)
    project = ProjectModel(
        id=pid,
        name="AI Test Project",
        description="",
        status=ProjectStatus.DRAFT_CREATED,
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    await db.commit()
    return pid


@pytest.fixture
def ai_run_service(db: AsyncSession) -> AIRunService:
    return AIRunService(db=db)


# ── Fallback flow ─────────────────────────────────────────────────────────────


async def test_fallback_flow_returns_valid_draft() -> None:
    flow = FallbackDocumentationFlow()
    result = await flow.run(
        DocumentationFlowInput(
            project_name="Library System",
            raw_requirements="We need a bot to manage book reservations.",
        )
    )
    assert isinstance(result, DocumentationFlowOutput)
    assert "Library System" in result.title
    assert len(result.content) > 0
    assert isinstance(result.assumptions, list)
    assert isinstance(result.risks, list)
    assert isinstance(result.suggested_next_steps, list)
    assert result.metadata.get("provider") == "fallback"


async def test_fallback_flow_content_includes_project_name() -> None:
    flow = FallbackDocumentationFlow()
    result = await flow.run(
        DocumentationFlowInput(
            project_name="Order Management",
            raw_requirements="Users place and track orders.",
        )
    )
    assert "Order Management" in result.title
    assert "Order Management" in result.content


async def test_fallback_flow_content_includes_raw_requirements() -> None:
    flow = FallbackDocumentationFlow()
    raw = "Users need to sign up and place orders via a Bale bot."
    result = await flow.run(
        DocumentationFlowInput(project_name="Order System", raw_requirements=raw)
    )
    assert raw in result.content


async def test_fallback_flow_includes_additional_context() -> None:
    flow = FallbackDocumentationFlow()
    result = await flow.run(
        DocumentationFlowInput(
            project_name="Survey Bot",
            raw_requirements="Collect survey answers.",
            additional_context="Must support Persian language.",
        )
    )
    assert "Must support Persian language." in result.content


async def test_fallback_flow_without_additional_context() -> None:
    flow = FallbackDocumentationFlow()
    result = await flow.run(
        DocumentationFlowInput(
            project_name="Simple Bot",
            raw_requirements="Just a simple greeting bot.",
        )
    )
    assert "Additional Context" not in result.content


def test_fallback_flow_is_documentation_flow_subclass() -> None:
    assert issubclass(FallbackDocumentationFlow, DocumentationFlow)


# ── Factory ───────────────────────────────────────────────────────────────────


def test_get_documentation_flow_returns_fallback_by_default() -> None:
    flow = get_documentation_flow("fallback")
    assert isinstance(flow, FallbackDocumentationFlow)


def test_get_documentation_flow_unknown_provider_returns_fallback() -> None:
    flow = get_documentation_flow("nonexistent_provider")
    assert isinstance(flow, FallbackDocumentationFlow)


def test_get_documentation_flow_uses_settings_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_DOCUMENTATION_PROVIDER", "fallback")
    # Re-load settings with the patched env
    import importlib
    import app.core.config as config_mod
    importlib.reload(config_mod)

    flow = get_documentation_flow()
    assert isinstance(flow, FallbackDocumentationFlow)

    importlib.reload(config_mod)  # restore


# ── AIRunService ──────────────────────────────────────────────────────────────


async def test_ai_run_service_creates_run_with_running_status(
    ai_run_service: AIRunService, project_id: UUID
) -> None:
    run = await ai_run_service.start(
        project_id=project_id,
        run_type=AIRunService.RUN_TYPE_DOCUMENTATION,
        input_data={"project_name": "Test", "raw_requirements": "..."},
    )
    assert run.status == AIRunStatus.RUNNING
    assert run.run_type == AIRunService.RUN_TYPE_DOCUMENTATION
    assert run.project_id == project_id
    assert run.finished_at is None
    assert run.error_message is None
    assert run.output_data is None


async def test_ai_run_service_complete_sets_completed_status(
    ai_run_service: AIRunService, project_id: UUID
) -> None:
    run = await ai_run_service.start(project_id, "documentation_flow", {})
    run = await ai_run_service.complete(run, {"title": "Draft", "content": "..."})
    assert run.status == AIRunStatus.COMPLETED
    assert run.output_data == {"title": "Draft", "content": "..."}
    assert run.finished_at is not None


async def test_ai_run_service_fail_sets_failed_status(
    ai_run_service: AIRunService, project_id: UUID
) -> None:
    run = await ai_run_service.start(project_id, "documentation_flow", {})
    run = await ai_run_service.fail(run, "LLM API key missing")
    assert run.status == AIRunStatus.FAILED
    assert run.error_message == "LLM API key missing"
    assert run.finished_at is not None


async def test_run_documentation_flow_records_completed(
    ai_run_service: AIRunService, project_id: UUID
) -> None:
    flow = FallbackDocumentationFlow()
    flow_input = DocumentationFlowInput(
        project_name="Task Manager",
        raw_requirements="Users create and assign tasks.",
    )
    run, output = await ai_run_service.run_documentation_flow(project_id, flow_input, flow)

    assert run.status == AIRunStatus.COMPLETED
    assert run.run_type == AIRunService.RUN_TYPE_DOCUMENTATION
    assert isinstance(output, DocumentationFlowOutput)
    assert output.title


async def test_run_documentation_flow_records_input_data(
    ai_run_service: AIRunService, project_id: UUID
) -> None:
    flow = FallbackDocumentationFlow()
    flow_input = DocumentationFlowInput(
        project_name="Survey Bot",
        raw_requirements="Collect responses.",
    )
    run, _ = await ai_run_service.run_documentation_flow(project_id, flow_input, flow)

    assert run.input_data is not None
    assert run.input_data["project_name"] == "Survey Bot"


async def test_run_documentation_flow_on_failure_records_failed_status(
    ai_run_service: AIRunService, project_id: UUID, db: AsyncSession
) -> None:
    class AlwaysFailingFlow(DocumentationFlow):
        async def run(self, input_data: DocumentationFlowInput) -> DocumentationFlowOutput:
            raise RuntimeError("Simulated LLM failure")

    flow_input = DocumentationFlowInput(
        project_name="Test", raw_requirements="Build a bot."
    )
    with pytest.raises(RuntimeError, match="Simulated LLM failure"):
        await ai_run_service.run_documentation_flow(
            project_id, flow_input, AlwaysFailingFlow()
        )

    from sqlalchemy import select
    from app.db.models.ai_runs import AIRunModel

    result = await db.execute(
        select(AIRunModel).where(AIRunModel.project_id == project_id)
    )
    runs = result.scalars().all()
    assert len(runs) == 1
    assert runs[0].status == AIRunStatus.FAILED
    assert "Simulated LLM failure" in runs[0].error_message


# ── Safety checks ─────────────────────────────────────────────────────────────


def test_no_generator_imports_in_ai_package() -> None:
    forbidden = {"app.generator", "app.services.generation_service"}
    for py_file in sorted(_AI_PACKAGE.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden, (
                        f"Forbidden import '{alias.name}' in {py_file.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert module not in forbidden, (
                    f"Forbidden import '{module}' in {py_file.name}"
                )
                for part in forbidden:
                    assert not module.startswith(part + "."), (
                        f"Forbidden import '{module}' in {py_file.name}"
                    )


def test_crewai_not_imported_at_module_level() -> None:
    crewai_file = _AI_PACKAGE / "crewai_documentation_flow.py"
    source = crewai_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("crewai"), (
                    "crewai must not be imported at module level in crewai_documentation_flow.py"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("crewai"), (
                "crewai must not be imported at module level in crewai_documentation_flow.py"
            )


async def test_crewai_flow_raises_runtime_error_when_crewai_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "crewai", None)  # type: ignore[arg-type]

    from app.ai.crewai_documentation_flow import CrewAIDocumentationFlow

    flow = CrewAIDocumentationFlow()
    with pytest.raises((RuntimeError, ImportError)):
        await flow.run(
            DocumentationFlowInput(project_name="X", raw_requirements="y")
        )


async def test_crewai_flow_does_not_write_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_crewai = types.ModuleType("crewai")
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = "# Generated document\n\nContent here."
    mock_crewai.Agent = MagicMock(return_value=MagicMock())
    mock_crewai.Task = MagicMock(return_value=MagicMock())
    mock_crewai.Crew = MagicMock(return_value=mock_crew_instance)
    mock_crewai.Process = MagicMock()
    mock_crewai.Process.sequential = "sequential"
    monkeypatch.setitem(sys.modules, "crewai", mock_crewai)

    before = set(tmp_path.rglob("*"))

    from app.ai.crewai_documentation_flow import CrewAIDocumentationFlow

    flow = CrewAIDocumentationFlow()
    result = await flow.run(
        DocumentationFlowInput(
            project_name="Test Project",
            raw_requirements="Build a task management bot.",
        )
    )

    after = set(tmp_path.rglob("*"))
    assert before == after, "CrewAI flow must not write any files"
    assert isinstance(result, DocumentationFlowOutput)
    assert result.metadata.get("provider") == "crewai"


async def test_crewai_flow_returns_documentation_flow_output_with_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_crewai = types.ModuleType("crewai")
    expected_content = "# My Project\n\n## Overview\n\nThis is the draft."
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = expected_content
    mock_crewai.Agent = MagicMock(return_value=MagicMock())
    mock_crewai.Task = MagicMock(return_value=MagicMock())
    mock_crewai.Crew = MagicMock(return_value=mock_crew_instance)
    mock_crewai.Process = MagicMock()
    mock_crewai.Process.sequential = "sequential"
    monkeypatch.setitem(sys.modules, "crewai", mock_crewai)

    from app.ai.crewai_documentation_flow import CrewAIDocumentationFlow

    flow = CrewAIDocumentationFlow()
    result = await flow.run(
        DocumentationFlowInput(
            project_name="My Project",
            raw_requirements="Manage events and attendees.",
        )
    )

    assert isinstance(result, DocumentationFlowOutput)
    assert result.content == expected_content
    assert "My Project" in result.title
    assert result.metadata["provider"] == "crewai"
