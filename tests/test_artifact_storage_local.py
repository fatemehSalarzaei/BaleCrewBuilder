from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import settings
from app.services.artifact_storage import (
    ArtifactStorageConfigurationError,
    ArtifactStoragePathError,
    LocalArtifactStorage,
    get_artifact_storage,
)


def test_local_storage_uses_configured_output_dir(tmp_path: Path) -> None:
    storage = LocalArtifactStorage(tmp_path)
    run_id = uuid4()

    assert storage.generation_run_dir(run_id) == tmp_path / str(run_id)
    assert storage.zip_path(run_id) == tmp_path / f"{run_id}.zip"


def test_local_storage_preserves_existing_file_artifact_path_behavior(
    tmp_path: Path,
) -> None:
    storage = LocalArtifactStorage(tmp_path)
    run_dir = tmp_path / "run"

    storage_path = storage.save_file_artifact(run_dir, "docs/README.md")

    assert storage_path == str(run_dir / "docs/README.md")


def test_local_storage_preserves_existing_zip_artifact_path_behavior(
    tmp_path: Path,
) -> None:
    storage = LocalArtifactStorage(tmp_path)
    zip_path = tmp_path / "artifact.zip"

    assert storage.save_zip_artifact(zip_path) == str(zip_path)


def test_local_storage_resolves_download_to_local_path(tmp_path: Path) -> None:
    storage = LocalArtifactStorage(tmp_path)
    zip_path = tmp_path / "artifact.zip"
    zip_path.write_bytes(b"zip-content")

    resolved = storage.resolve_download(str(zip_path))

    assert resolved.path == zip_path.resolve(strict=False)
    assert storage.exists(str(zip_path)) is True


def test_local_storage_reports_missing_file(tmp_path: Path) -> None:
    storage = LocalArtifactStorage(tmp_path)

    assert storage.exists(str(tmp_path / "missing.zip")) is False


def test_local_storage_rejects_empty_storage_path(tmp_path: Path) -> None:
    storage = LocalArtifactStorage(tmp_path)

    with pytest.raises(ArtifactStoragePathError, match="storage path is empty"):
        storage.resolve_download("")


def test_get_artifact_storage_rejects_unsupported_backend() -> None:
    original = settings.artifact_storage_backend
    settings.artifact_storage_backend = "s3"
    try:
        with pytest.raises(ArtifactStorageConfigurationError, match="Unsupported"):
            get_artifact_storage()
    finally:
        settings.artifact_storage_backend = original
