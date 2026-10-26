from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from bootstrap.reference.docs import setup_docs_routes
from bootstrap.reference.openapi import custom_openapi
from bootstrap.reference.swagger import servers, tags_metadata
from bootstrap.security import disable_cors_debug, production_cors
from common.config import settings
from common.exceptions.filter import setup_exception_handlers
from context.router import api_router
from infrastructure.database.session import create_tables, engine
from observability.health.controller import router as health_router
from observability.logger import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting {} v{}", settings.PROJECT_NAME, settings.APP_VERSION)
    if settings.DATABASE_CREATE_TABLES:
        await create_tables()
    yield
    await engine.dispose()
    logger.info("{} stopped", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    current_app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESC,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        openapi_tags=tags_metadata,
        servers=servers,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    current_app.include_router(api_router)
    current_app.include_router(health_router)
    setup_exception_handlers(current_app)
    current_app.openapi = custom_openapi(current_app)  # type: ignore[method-assign]
    setup_docs_routes(current_app)
    if settings.CORS_DISABLE:
        disable_cors_debug(current_app)
    else:
        production_cors(current_app, settings.CORS_REGEX)
    return current_app


app = create_app()
