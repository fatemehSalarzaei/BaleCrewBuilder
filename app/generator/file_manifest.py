import hashlib
import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas.blueprint import BotBlueprint
from app.services.validation_service import ValidationResult


class ManifestValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)


class ManifestTestCommandResult(BaseModel):
    command: str
    exit_code: int | None = None
    status: str
    output: str | None = None


class GenerationManifest(BaseModel):
    blueprint_hash: str
    template_profile: str
    template_version: str = "unversioned"
    enabled_modules: list[str]
    custom_logic_blocks: list[str]
    generated_files: list[str]
    generated_at: str  # ISO 8601
    validation_result: ManifestValidationResult | None = None
    test_command_results: list[ManifestTestCommandResult] = Field(default_factory=list)


def compute_blueprint_hash(blueprint: BotBlueprint) -> str:
    serialized = json.dumps(
        blueprint.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_manifest(
    blueprint: BotBlueprint,
    generated_files: list[str],
    *,
    validation_result: ValidationResult | None = None,
    test_command_results: list[ManifestTestCommandResult] | None = None,
    template_version: str = "unversioned",
) -> GenerationManifest:
    manifest_validation = (
        ManifestValidationResult(
            is_valid=validation_result.is_valid,
            errors=list(validation_result.errors),
        )
        if validation_result is not None
        else None
    )
    return GenerationManifest(
        blueprint_hash=compute_blueprint_hash(blueprint),
        template_profile=blueprint.generation.template_profile,
        template_version=template_version,
        enabled_modules=sorted(blueprint.generation.enabled_modules),
        custom_logic_blocks=sorted(blueprint.generation.custom_logic_blocks),
        generated_files=sorted(generated_files),
        generated_at=datetime.now(timezone.utc).isoformat(),
        validation_result=manifest_validation,
        test_command_results=test_command_results or [],
    )
