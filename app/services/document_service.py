from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_documents import ProjectDocumentModel
from app.schemas.document import DocumentCreate, DocumentRead


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"Document {document_id} not found")
        self.document_id = document_id


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, document_id: UUID, project_id: UUID) -> DocumentRead:
        stmt = sa.select(ProjectDocumentModel).where(
            ProjectDocumentModel.id == document_id,
            ProjectDocumentModel.project_id == project_id,
        )
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            raise DocumentNotFoundError(document_id)
        return DocumentRead.model_validate(row)

    async def create(self, project_id: UUID, payload: DocumentCreate) -> DocumentRead:
        row = ProjectDocumentModel(
            id=uuid4(),
            project_id=project_id,
            kind=payload.kind,
            title=payload.title,
            content=payload.content,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.commit()
        return DocumentRead.model_validate(row)

    async def get_latest_for_project(self, project_id: UUID) -> DocumentRead | None:
        stmt = (
            sa.select(ProjectDocumentModel)
            .where(ProjectDocumentModel.project_id == project_id)
            .order_by(ProjectDocumentModel.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return DocumentRead.model_validate(row)

    async def list_for_project(self, project_id: UUID) -> list[DocumentRead]:
        stmt = (
            sa.select(ProjectDocumentModel)
            .where(ProjectDocumentModel.project_id == project_id)
            .order_by(ProjectDocumentModel.created_at)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [DocumentRead.model_validate(r) for r in rows]
