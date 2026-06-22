from datetime import datetime, timezone
from uuid import UUID, uuid4

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
    ApprovalDecision.REJECT: ProjectStatus.DOCUMENT_CHANGE_REQUESTED,
    ApprovalDecision.SPLIT_SCOPE: ProjectStatus.DOCUMENT_CHANGE_REQUESTED,
    ApprovalDecision.FREEZE_SCOPE: ProjectStatus.DOCUMENT_APPROVED,  # no state change, scope locked
}


class ApprovalService:
    def __init__(self, project_service: ProjectService) -> None:
        self._project_service = project_service
        self._store: dict[UUID, ReviewRead] = {}
        self._by_project: dict[UUID, list[UUID]] = {}

    def _record(
        self,
        project_id: UUID,
        decision: ApprovalDecision,
        feedback: str,
        reviewer_name: str | None,
        document_id: UUID | None,
    ) -> ReviewRead:
        project = self._project_service.get(project_id)
        required = _REQUIRED_STATUS[decision]
        if project.status != required:
            raise InvalidDecisionForStatusError(decision, project.status)

        previous_status = project.status
        next_status = _NEXT_STATUS[decision]

        if next_status != previous_status:
            self._project_service.transition(project_id, next_status)

        review = ReviewRead(
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
        self._store[review.id] = review
        self._by_project.setdefault(project_id, []).append(review.id)
        return review

    def approve(self, project_id: UUID, payload: DocumentApproveCreate) -> ReviewRead:
        return self._record(
            project_id=project_id,
            decision=ApprovalDecision.APPROVE,
            feedback=payload.feedback,
            reviewer_name=payload.reviewer_name,
            document_id=payload.document_id,
        )

    def submit_feedback(self, project_id: UUID, payload: DocumentFeedbackCreate) -> ReviewRead:
        return self._record(
            project_id=project_id,
            decision=payload.decision,
            feedback=payload.feedback,
            reviewer_name=payload.reviewer_name,
            document_id=payload.document_id,
        )

    def list_for_project(self, project_id: UUID) -> list[ReviewRead]:
        ids = self._by_project.get(project_id, [])
        return [self._store[rid] for rid in ids]
