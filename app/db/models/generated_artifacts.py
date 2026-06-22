import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedArtifactModel(Base):
    __tablename__ = "generated_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    generation_run_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("generation_runs.id")
    )
    artifact_type: Mapped[str] = mapped_column(sa.String(100))
    filename: Mapped[str] = mapped_column(sa.String(500))
    storage_path: Mapped[str] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
