from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document_reviews import DocumentReviewModel
from app.schemas.approval import (
    ApprovalDecision,
    DocumentApproveCreate,
    DocumentFeedbackCreate,
    ReviewRead,
)
from app.schemas.project import ProjectStatus
from app.services.project_service import ProjectService


class InvalidDecisionForStatusError(Exception):
    def __init__(self, decision: ApprovalDecision, current_status: ProjectStatus) -> None:
        self.decision = decision
        self.current_status = current_status
        super().__init__(
            f"Decision {decision} is not allowed when project status is {current_status}"
        )


_REQUIRED_STATUS: dict[ApprovalDecision, ProjectStatus] = {
    ApprovalDecision.APPROVE: ProjectStatus.DOCUMENT_REVIEW_PENDING,
    ApprovalDecision.REQUEST_CHANGES: ProjectStatus.DOCUMENT_REVIEW_PENDING,
    ApprovalDecision.REJECT: ProjectStatus.DOCUMENT_REVIEW_PENDING,
    ApprovalDecision.SPLIT_SCOPE: ProjectStatus.DOCUMENT_REVIEW_PENDING,
    ApprovalDecision.FREEZE_SCOPE: ProjectStatus.DOCUMENT_APPROVED,
}

_NEXT_STATUS: dict[ApprovalDecision, ProjectStatus] = {
    ApprovalDecision.APPROVE: ProjectStatus.DOCUMENT_APPROVED,
    ApprovalDecision.REQUEST_CHANGES: ProjectStatus.DOCUMENT_CHANGE_REQUESTED,
    ApprovalDecision.REJECT: ProjectStatus.DOCUMENT_REJECTED,
    ApprovalDecision.SPLIT_SCOPE: ProjectStatus.DOCUMENT_CHANGE_REQUESTED,
    ApprovalDecision.FREEZE_SCOPE: ProjectStatus.DOCUMENT_APPROVED,
}


class ApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._project_service = ProjectService(db=db)

    async def _record(
        self,
        project_id: UUID,
        decision: ApprovalDecision,
        feedback: str,
        reviewer_name: str | None,
        document_id: UUID | None,
    ) -> ReviewRead:
        project = await self._project_service.get(project_id)
        required = _REQUIRED_STATUS[decision]
        if project.status != required:
            raise InvalidDecisionForStatusError(decision, project.status)

        previous_status = project.status
        next_status = _NEXT_STATUS[decision]

        if next_status != previous_status:
            await self._project_service.transition(project_id, next_status)

        row = DocumentReviewModel(
            id=uuid4(),
            project_id=project_id,
            document_id=document_id,
            reviewer_name=reviewer_name,
            decision=decision,
            feedback=feedback,
            previous_status=previous_status,
            next_status=next_status,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.commit()
        return ReviewRead.model_validate(row)

    async def approve(self, project_id: UUID, payload: DocumentApproveCreate) -> ReviewRead:
        return await self._record(
            project_id=project_id,
            decision=ApprovalDecision.APPROVE,
            feedback=payload.feedback,
            reviewer_name=payload.reviewer_name,
            document_id=payload.document_id,
        )

    async def submit_feedback(
        self, project_id: UUID, payload: DocumentFeedbackCreate
    ) -> ReviewRead:
        return await self._record(
            project_id=project_id,
            decision=payload.decision,
            feedback=payload.feedback,
            reviewer_name=payload.reviewer_name,
            document_id=payload.document_id,
        )

    async def list_for_project(self, project_id: UUID) -> list[ReviewRead]:
        stmt = (
            sa.select(DocumentReviewModel)
            .where(DocumentReviewModel.project_id == project_id)
            .order_by(DocumentReviewModel.created_at)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [ReviewRead.model_validate(r) for r in rows]
