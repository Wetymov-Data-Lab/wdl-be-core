from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.services.column import load_accessible_column
from context.application.services.table import load_accessible_table
from context.application.use_case import UseCase
from context.domain.entities.relationship import Relationship, RelationshipAttributes
from context.infrastructure.repositories.relationship_contract import RelationshipUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService

DUPLICATE_MAPPINGS = "Relationship contains duplicate column mappings"


@dataclass(frozen=True, slots=True)
class CreateRelationshipRequest:
    database_id: UUID
    source_table_id: UUID
    target_table_id: UUID
    attributes: RelationshipAttributes
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateRelationshipRequest:
    relationship_id: UUID
    attributes: RelationshipAttributes


class ListRelationships(UseCase[UUID, list[Relationship]]):
    def __init__(self, uow: RelationshipUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> list[Relationship]:
        await self._authorization.require_database(request)
        async with self._uow:
            return await self._uow.relationships.list(request)


class GetRelationship(UseCase[UUID, Relationship]):
    def __init__(self, uow: RelationshipUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> Relationship:
        await self._authorization.require_relationship(request)
        async with self._uow:
            return await get_relationship(self._uow, request)


class CreateRelationship(UseCase[CreateRelationshipRequest, Relationship]):
    def __init__(self, uow: RelationshipUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: CreateRelationshipRequest) -> Relationship:
        await self._authorization.require_database(request.database_id)
        async with self._uow:
            source = await load_accessible_table(
                self._authorization, self._uow.tables, request.source_table_id
            )
            target = await load_accessible_table(
                self._authorization, self._uow.tables, request.target_table_id
            )
            relationship = Relationship.create(
                database_id=request.database_id,
                source_table_id=request.source_table_id,
                target_table_id=request.target_table_id,
                attributes=request.attributes,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            relationship.ensure_endpoint_tables(source, target)
            await ensure_column_pairs(
                self._uow, self._authorization, relationship, request.attributes
            )
            await self._uow.relationships.add(relationship)
            await commit_or_conflict(
                self._uow, f"Relationship '{request.attributes.name}' already exists"
            )
            await self._uow.relationships.add_columns(relationship)
            await commit_or_conflict(self._uow, DUPLICATE_MAPPINGS)
            return relationship


class UpdateRelationship(UseCase[UpdateRelationshipRequest, Relationship]):
    def __init__(self, uow: RelationshipUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UpdateRelationshipRequest) -> Relationship:
        await self._authorization.require_relationship(request.relationship_id)
        async with self._uow:
            relationship = await get_relationship(self._uow, request.relationship_id)
            await ensure_column_pairs(
                self._uow, self._authorization, relationship, request.attributes
            )
            relationship.update(attributes=request.attributes, updated_at=datetime.now(UTC))
            await self._uow.relationships.save(relationship)
            await self._uow.relationships.replace_columns(relationship)
            await commit_or_conflict(self._uow, DUPLICATE_MAPPINGS)
            return relationship


class DeleteRelationship(UseCase[UUID, None]):
    def __init__(self, uow: RelationshipUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> None:
        await self._authorization.require_relationship(request)
        async with self._uow:
            relationship = await get_relationship(self._uow, request)
            await self._uow.relationships.remove(relationship)
            await self._uow.commit()


async def get_relationship(uow: RelationshipUnitOfWork, relationship_id: UUID) -> Relationship:
    relationship = await uow.relationships.get(relationship_id)
    if relationship is None:
        raise EntityNotFoundError(f"Relationship {relationship_id} was not found")
    return relationship


async def ensure_column_pairs(
    uow: RelationshipUnitOfWork,
    authorization: AuthorizationService,
    relationship: Relationship,
    attributes: RelationshipAttributes,
) -> None:
    """Check access to every mapped column and that it belongs to its endpoint table."""
    for pair in attributes.columns:
        source = await load_accessible_column(authorization, uow.columns, pair.source_column_id)
        target = await load_accessible_column(authorization, uow.columns, pair.target_column_id)
        relationship.ensure_column_pair(source, target)
