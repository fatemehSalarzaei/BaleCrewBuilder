from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import get_artifact_service
from app.services.artifact_service import (
    ArtifactService,
    ArtifactStoragePathError,
    NoCompletedGenerationRunError,
    ZipArtifactFileMissingError,
    ZipArtifactNotFoundError,
)
from app.services.project_service import ProjectNotFoundError

router = APIRouter(prefix="/projects", tags=["artifacts"])


@router.get("/{project_id}/download", response_class=FileResponse)
async def download_latest_project_zip(
    project_id: UUID,
    artifact_svc: Annotated[ArtifactService, Depends(get_artifact_service)],
) -> FileResponse:
    try:
        artifact = await artifact_svc.get_latest_project_zip(project_id)
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    except NoCompletedGenerationRunError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No completed generation run found for project",
        )
    except ZipArtifactNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ZIP artifact found for latest completed generation run",
        )
    except ZipArtifactFileMissingError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="ZIP artifact file is missing on disk",
        )
    except ArtifactStoragePathError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return FileResponse(
        path=artifact.path,
        media_type="application/zip",
        filename=artifact.filename,
    )
