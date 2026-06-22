from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.routes.approvals import router as approvals_router
from app.api.routes.blueprints import router as blueprints_router
from app.api.routes.documents import router as documents_router
from app.api.routes.generator import router as generator_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router


def create_app() -> FastAPI:
    configure_logging()

    application = FastAPI(
        title="Bale Bot Builder Platform",
        description="Platform for generating Bale bot projects from approved documents and validated blueprints.",
        version="0.1.0",
        debug=settings.debug,
    )

    application.include_router(health_router)
    application.include_router(projects_router)
    application.include_router(documents_router)
    application.include_router(approvals_router)
    application.include_router(blueprints_router)
    application.include_router(generator_router)

    return application


app = create_app()
