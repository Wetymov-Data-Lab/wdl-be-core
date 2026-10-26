from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def disable_cors_debug(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def production_cors(app: FastAPI, allow_origin_regex: str) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
