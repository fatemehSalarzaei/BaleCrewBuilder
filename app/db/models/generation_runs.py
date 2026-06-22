import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GenerationRunModel(Base):
    __tablename__ = "generation_runs"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("projects.id"))
    blueprint_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("blueprints.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(sa.String(50))
    template_profile: Mapped[str] = mapped_column(sa.String(200))
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
