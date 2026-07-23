from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from wdl_be_core.domain.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from wdl_be_core.infrastructure.database.base import Base


async def get_or_404[ModelT: Base](
    session: AsyncSession,
    model: type[ModelT],
    entity_id: UUID,
) -> ModelT:
    entity = await session.get(model, entity_id)
    if entity is None:
        raise EntityNotFoundError(f"{model.__name__} {entity_id} was not found")
    return entity


async def commit_or_conflict(session: AsyncSession, detail: str) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise EntityAlreadyExistsError(detail) from error


async def flush_or_conflict(session: AsyncSession, detail: str) -> None:
    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        raise EntityAlreadyExistsError(detail) from error


def apply_values(entity: Base, values: dict[str, Any]) -> None:
    for field, value in values.items():
        setattr(entity, field, value)
