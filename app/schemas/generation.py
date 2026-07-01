from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerationRunStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenerationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    blueprint_id: UUID | None
    status: str
    template_profile: str
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    artifacts: list["GeneratedArtifactRead"] = Field(default_factory=list)
    download_url: str | None = None


class GeneratedArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artifact_type: str
    filename: str
    created_at: datetime
