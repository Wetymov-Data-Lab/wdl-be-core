from fastapi import APIRouter
from wdl_shared.schemas.engine.common.health import HealthResponse

from wdl_be_core.presentation.api.routers.canvas import router as canvas_router
from wdl_be_core.presentation.api.routers.database import router as database_router
from wdl_be_core.presentation.api.routers.projects import router as projects_router
from wdl_be_core.presentation.api.routers.realm import router as realm_router
from wdl_be_core.presentation.api.routers.relationships import router as relationships_router

api_router = APIRouter()

api_router.include_router(realm_router)
api_router.include_router(projects_router)
api_router.include_router(database_router)
api_router.include_router(relationships_router)
api_router.include_router(canvas_router)


@api_router.get("/health", tags=["system"], response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
