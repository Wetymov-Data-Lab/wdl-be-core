from fastapi import FastAPI

from wdl_be_core.infrastructure.config import settings
from wdl_be_core.infrastructure.cors import disable_cors_debug, production_cors
from wdl_be_core.presentation.api.router import api_router
from wdl_be_core.presentation.api.swagger.docs import setup_docs_routes
from wdl_be_core.presentation.api.swagger.openapi import custom_openapi
from wdl_be_core.presentation.api.swagger.swagger import servers, tags_metadata


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
