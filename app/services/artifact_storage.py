from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.core.config import settings


class ArtifactStorageConfigurationError(ValueError):
    pass


class ArtifactStoragePathError(Exception):
    pass


@dataclass(frozen=True)
class ResolvedArtifact:
    path: Path


class LocalArtifactStorage:
    """Local filesystem artifact storage.

    This is the default development/test implementation. It keeps the existing
    database contract by storing local paths in GeneratedArtifactModel.storage_path.
    """

    def __init__(self, output_dir: Path | str | None = None) -> None:
        self.output_dir = Path(output_dir or settings.generation_output_dir)

    def generation_run_dir(self, run_id: UUID) -> Path:
        return self.output_dir / str(run_id)

    def zip_path(self, run_id: UUID) -> Path:
        return self.output_dir / f"{run_id}.zip"

    def save_file_artifact(self, run_output_dir: Path, rel_path: str) -> str:
        return str(run_output_dir / rel_path)

    def save_zip_artifact(self, zip_path: Path) -> str:
        return str(zip_path)

    def resolve_download(self, storage_path: str) -> ResolvedArtifact:
        if not storage_path:
            raise ArtifactStoragePathError("Artifact storage path is empty")
        return ResolvedArtifact(path=Path(storage_path).resolve(strict=False))

    def exists(self, storage_path: str) -> bool:
        return self.resolve_download(storage_path).path.is_file()


def get_artifact_storage() -> LocalArtifactStorage:
    if settings.artifact_storage_backend != "local":
        raise ArtifactStorageConfigurationError(
            f"Unsupported artifact storage backend: {settings.artifact_storage_backend}"
        )
    return LocalArtifactStorage(settings.generation_output_dir)
