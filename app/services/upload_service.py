from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.uploaded_files import UploadedFileModel
from app.schemas.uploaded_file import UploadedFileRead


class UploadService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def store_metadata(
        self,
        project_id: UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> UploadedFileRead:
        file_id = uuid4()
        row = UploadedFileModel(
            id=file_id,
            project_id=project_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=f"uploads/{project_id}/{file_id}/{filename}",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.commit()
        return UploadedFileRead.model_validate(row)

    async def list_for_project(self, project_id: UUID) -> list[UploadedFileRead]:
        import sqlalchemy as sa

        stmt = (
            sa.select(UploadedFileModel)
            .where(UploadedFileModel.project_id == project_id)
            .order_by(UploadedFileModel.created_at)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [UploadedFileRead.model_validate(r) for r in rows]
