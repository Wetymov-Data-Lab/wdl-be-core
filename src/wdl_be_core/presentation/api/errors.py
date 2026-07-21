from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from wdl_be_core.domain.exceptions import (
    DomainError,
    EntityNotFoundError,
    InvalidRealmNameError,
    RealmAlreadyExistsError,
)


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundError)
    async def not_found(_: Request, error: EntityNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)})

    @app.exception_handler(RealmAlreadyExistsError)
    async def conflict(_: Request, error: RealmAlreadyExistsError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)})

    @app.exception_handler(InvalidRealmNameError)
    async def invalid_name(_: Request, error: InvalidRealmNameError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(error)},
        )

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(error)})
