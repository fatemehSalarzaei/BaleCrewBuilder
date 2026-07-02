from pathlib import Path

from app.generator.template_registry import TemplateRegistry
from app.schemas.blueprint import BotBlueprint
from app.services.validation_service import BlueprintValidationService, ValidationResult


class GeneratorError(Exception):
    pass


class PathTraversalError(GeneratorError):
    pass


class DuplicatePathError(GeneratorError):
    pass


class InvalidBlueprintForGenerationError(GeneratorError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(
            "Blueprint failed generator precondition validation:\n"
            + "\n".join(f"- {error}" for error in errors)
        )


GeneratorValidationError = InvalidBlueprintForGenerationError


def assert_safe_path(relative_path: str, output_root: Path) -> Path:
    if "\x00" in relative_path:
        raise PathTraversalError(f"Null bytes are not allowed in paths: {relative_path!r}")
    path = Path(relative_path)
    if path.is_absolute():
        raise PathTraversalError(f"Absolute paths are not allowed: {relative_path!r}")
    resolved = (output_root / path).resolve()
    try:
        resolved.relative_to(output_root.resolve())
    except ValueError:
        raise PathTraversalError(f"Path escapes output root: {relative_path!r}")
    return resolved


def assert_no_duplicate_paths(paths: list[str]) -> None:
    seen: set[str] = set()
    for p in paths:
        normalized = Path(p).as_posix()
        if normalized in seen:
            raise DuplicatePathError(f"Duplicate output path detected: {normalized!r}")
        seen.add(normalized)


def assert_generator_preconditions(
    blueprint: BotBlueprint,
    registry: TemplateRegistry,
    validation_result: ValidationResult | None = None,
) -> ValidationResult:
    registry.validate_profile(blueprint.generation.template_profile)
    registry.validate_modules(blueprint.generation.enabled_modules)

    validation = validation_result or BlueprintValidationService().validate(blueprint)
    if not validation.is_valid:
        raise InvalidBlueprintForGenerationError(validation.errors)
    return validation
