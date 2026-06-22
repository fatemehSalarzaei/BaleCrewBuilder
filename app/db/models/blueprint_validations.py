import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BlueprintValidationModel(Base):
    __tablename__ = "blueprint_validations"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("blueprints.id")
    )
    is_valid: Mapped[bool] = mapped_column(sa.Boolean)
    errors: Mapped[list[Any]] = mapped_column(sa.JSON)
    validated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
