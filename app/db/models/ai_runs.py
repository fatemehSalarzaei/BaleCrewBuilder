import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIRunModel(Base):
    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("projects.id"))
    run_type: Mapped[str] = mapped_column(sa.String(100))
    status: Mapped[str] = mapped_column(sa.String(50))
    input_data: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
