# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS development

WORKDIR /workspace/wdl-be-core
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

COPY --from=wdl_shared . /workspace/wdl-shared
COPY . /workspace/wdl-be-core
RUN uv sync --frozen --all-groups

CMD ["uv", "run", "uvicorn", "wdl_be_core.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS production

WORKDIR /workspace/wdl-be-core
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=wdl_shared . /workspace/wdl-shared
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "wdl_be_core.main:app", "--host", "0.0.0.0", "--port", "8000"]
