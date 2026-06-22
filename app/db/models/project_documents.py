import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectDocumentModel(Base):
    __tablename__ = "project_documents"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("projects.id"))
    kind: Mapped[str] = mapped_column(sa.String(50))
    title: Mapped[str] = mapped_column(sa.String(300))
    content: Mapped[str] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
