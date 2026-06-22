from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.project import ProjectStatus


class ApprovalDecision(StrEnum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    REJECT = "REJECT"
    SPLIT_SCOPE = "SPLIT_SCOPE"
    FREEZE_SCOPE = "FREEZE_SCOPE"


class DocumentFeedbackCreate(BaseModel):
    """Payload for non-approve review decisions (REQUEST_CHANGES, REJECT, SPLIT_SCOPE, FREEZE_SCOPE)."""

    decision: ApprovalDecision
    feedback: str = Field(min_length=1, max_length=5000)
    reviewer_name: str | None = Field(default=None, max_length=200)
    document_id: UUID | None = Field(default=None)

    @model_validator(mode="after")
    def decision_must_not_be_approve(self) -> "DocumentFeedbackCreate":
        if self.decision == ApprovalDecision.APPROVE:
            raise ValueError(
                "APPROVE is not valid here; use POST /document/approve instead"
            )
        return self


class DocumentApproveCreate(BaseModel):
    """Payload for document approval (APPROVE decision)."""

    feedback: str = Field(default="", max_length=5000)
    reviewer_name: str | None = Field(default=None, max_length=200)
    document_id: UUID | None = Field(default=None)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    document_id: UUID | None
    reviewer_name: str | None
    decision: ApprovalDecision
    feedback: str
    previous_status: ProjectStatus
    next_status: ProjectStatus
    created_at: datetime
