from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.document import DocumentRead


class UploadedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    uploaded_file: UploadedFileRead
    extracted_text: str
    document: DocumentRead | None = None
