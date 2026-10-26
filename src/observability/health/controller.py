from fastapi import APIRouter
from wdl_shared.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", tags=["system"], response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
