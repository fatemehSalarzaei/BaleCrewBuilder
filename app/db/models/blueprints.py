import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BlueprintModel(Base):
    __tablename__ = "blueprints"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("projects.id"), unique=True
    )
    blueprint_data: Mapped[dict[str, Any]] = mapped_column(sa.JSON)
    stored_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
