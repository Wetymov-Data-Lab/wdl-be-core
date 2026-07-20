from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from wdl_be_core.infrastructure.config import settings
from wdl_be_core.infrastructure.cors import disable_cors_debug, production_cors
from wdl_be_core.infrastructure.database.session import create_tables, engine
from wdl_be_core.presentation.api.router import api_router
from wdl_be_core.presentation.api.swagger.docs import setup_docs_routes
from wdl_be_core.presentation.api.swagger.openapi import custom_openapi
from wdl_be_core.presentation.api.swagger.swagger import servers, tags_metadata


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.DATABASE_CREATE_TABLES:
        await create_tables()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    current_app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESC,
        version=settings.APP_VERSION,
        debug=bool(settings.DEBUG),
        openapi_tags=tags_metadata,
        servers=servers,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    current_app.include_router(api_router)
    current_app.openapi = custom_openapi(current_app)  # type: ignore[method-assign]
    setup_docs_routes(current_app)
    if settings.CORS_DISABLE:
        disable_cors_debug(current_app)
    else:
        production_cors(current_app, settings.CORS_REGEX)
    return current_app


app = create_app()
