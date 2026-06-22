import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UploadedFileModel(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("projects.id"))
    filename: Mapped[str] = mapped_column(sa.String(500))
    content_type: Mapped[str] = mapped_column(sa.String(200))
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger)
    storage_path: Mapped[str] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
