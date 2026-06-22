import hashlib
import json
from datetime import datetime, timezone

from pydantic import BaseModel

from app.schemas.blueprint import BotBlueprint


class GenerationManifest(BaseModel):
    blueprint_hash: str
    template_profile: str
    enabled_modules: list[str]
    custom_logic_blocks: list[str]
    generated_files: list[str]
    generated_at: str  # ISO 8601


def compute_blueprint_hash(blueprint: BotBlueprint) -> str:
    serialized = json.dumps(
        blueprint.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_manifest(blueprint: BotBlueprint, generated_files: list[str]) -> GenerationManifest:
    return GenerationManifest(
        blueprint_hash=compute_blueprint_hash(blueprint),
        template_profile=blueprint.generation.template_profile,
        enabled_modules=sorted(blueprint.generation.enabled_modules),
        custom_logic_blocks=sorted(blueprint.generation.custom_logic_blocks),
        generated_files=sorted(generated_files),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
