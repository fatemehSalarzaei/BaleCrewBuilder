import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentReviewModel(Base):
    __tablename__ = "document_reviews"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("projects.id"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("project_documents.id"), nullable=True
    )
    reviewer_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    decision: Mapped[str] = mapped_column(sa.String(50))
    feedback: Mapped[str] = mapped_column(sa.Text)
    previous_status: Mapped[str] = mapped_column(sa.String(50))
    next_status: Mapped[str] = mapped_column(sa.String(50))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
