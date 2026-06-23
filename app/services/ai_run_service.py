from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.documentation_flow import DocumentationFlow
from app.db.models.ai_runs import AIRunModel
from app.schemas.ai import AIRunStatus, DocumentationFlowInput, DocumentationFlowOutput


class AIRunService:
    RUN_TYPE_DOCUMENTATION = "documentation_flow"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def start(
        self,
        project_id: UUID,
        run_type: str,
        input_data: dict[str, Any],
    ) -> AIRunModel:
        now = datetime.now(timezone.utc)
        run = AIRunModel(
            id=uuid4(),
            project_id=project_id,
            run_type=run_type,
            status=AIRunStatus.RUNNING,
            input_data=input_data,
            started_at=now,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def complete(self, run: AIRunModel, output_data: dict[str, Any]) -> AIRunModel:
        run.status = AIRunStatus.COMPLETED
        run.output_data = output_data
        run.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def fail(self, run: AIRunModel, error_message: str) -> AIRunModel:
        run.status = AIRunStatus.FAILED
        run.error_message = error_message
        run.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def run_documentation_flow(
        self,
        project_id: UUID,
        flow_input: DocumentationFlowInput,
        flow: DocumentationFlow,
    ) -> tuple[AIRunModel, DocumentationFlowOutput]:
        run = await self.start(
            project_id=project_id,
            run_type=self.RUN_TYPE_DOCUMENTATION,
            input_data=flow_input.model_dump(),
        )
        try:
            output = await flow.run(flow_input)
        except Exception as exc:
            await self.fail(run, str(exc))
            raise
        run = await self.complete(run, output.model_dump())
        return run, output
