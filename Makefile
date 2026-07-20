.PHONY: env install dev lint format typecheck test check migrate migration docker-up docker-down

env:
	[ -f .env.example ] && cp -f .env.example .env || echo '.env.example not found'

install:
	uv sync --all-groups

dev:
	uv run uvicorn wdl_be_core.main:app --reload

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

test:
	uv run pytest

check: lint typecheck test

migrate:
	uv run alembic upgrade head

migration:
	uv run alembic revision --autogenerate -m "$(name)"

docker-up:
	docker compose up --build

docker-down:
	docker compose down
