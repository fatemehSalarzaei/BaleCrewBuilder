from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentKind(StrEnum):
    RAW_TEXT = "RAW_TEXT"
    MARKDOWN = "MARKDOWN"


class DocumentCreate(BaseModel):
    kind: DocumentKind = DocumentKind.MARKDOWN
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    kind: DocumentKind
    title: str
    content: str
    created_at: datetime


class DocumentGenerateRequest(BaseModel):
    raw_requirements: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=300)
    additional_context: str | None = None


class DocumentGenerateResponse(BaseModel):
    document: DocumentRead
    ai_run_id: UUID
    ai_run_status: str
