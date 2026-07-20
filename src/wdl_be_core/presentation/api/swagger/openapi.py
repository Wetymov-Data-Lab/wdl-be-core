from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from wdl_be_core.infrastructure.config import settings


def custom_openapi(app: FastAPI) -> Callable[[], dict[str, Any]]:
    def generate_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        app.openapi_schema = get_openapi(
            title=settings.PROJECT_NAME,
            version=settings.APP_VERSION,
            description=settings.PROJECT_DESC,
            tags=app.openapi_tags,
            servers=app.servers,
            routes=app.routes,
        )
        return app.openapi_schema

    return generate_openapi
