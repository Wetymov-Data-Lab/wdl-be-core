from fastapi import APIRouter
from .routers import realm
from wdl_shared.schemas.engine.common import HealthResponse

api_router = APIRouter()

api_router.include_router(realm.router)

@api_router.get("/health", tags=["system"], response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
