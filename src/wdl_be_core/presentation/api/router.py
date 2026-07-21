from fastapi import APIRouter
from wdl_shared.schemas.engine.common.health import HealthResponse

from wdl_be_core.presentation.api.routers.realm import router as realm_router

api_router = APIRouter()

api_router.include_router(realm_router)


@api_router.get("/health", tags=["system"], response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
