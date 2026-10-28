from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from wdl_shared.schemas.engine.models.database import (
    IndexColumnModel,
    IndexCreateModel,
    IndexResponseModel,
    IndexUpdateModel,
    RelationshipColumnPair,
    RelationshipCreateModel,
    RelationshipResponseModel,
    RelationshipUpdateModel,
)

from common.services.identity import CurrentUser
from context.application.services.index import (
    CreateIndex,
    CreateIndexRequest,
    DeleteIndex,
    GetIndex,
    ListIndexes,
    UpdateIndex,
    UpdateIndexRequest,
)
from context.application.services.relationship import (
    CreateRelationship,
    CreateRelationshipRequest,
    DeleteRelationship,
    GetRelationship,
    ListRelationships,
    UpdateRelationship,
    UpdateRelationshipRequest,
)
from context.domain.entities.index import DiagramIndex, IndexAttributes, IndexColumn
from context.domain.entities.relationship import (
    ColumnPair,
    Relationship,
    RelationshipAttributes,
)
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.guards.authorization import get_authorization_service
from context.infrastructure.repositories.dependencies import get_realm_uow
from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService

router = APIRouter(tags=["database relationships"], dependencies=[Depends(get_current_user)])
SchemaUow = Annotated[SQLAlchemyUnitOfWork, Depends(get_realm_uow)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
Authorization = Annotated[AuthorizationService, Depends(get_authorization_service)]


def index_attributes(body: IndexCreateModel | IndexUpdateModel) -> IndexAttributes:
    return IndexAttributes(
        name=body.name,
        type=body.type,
        columns=tuple(
            IndexColumn(
                column_id=column.column_id,
                sort_order=column.sort_order,
                position=column.position,
            )
            for column in body.columns
        ),
        method=body.method,
        where=body.where,
    )


def relationship_attributes(
    body: RelationshipCreateModel | RelationshipUpdateModel,
) -> RelationshipAttributes:
    return RelationshipAttributes(
        name=body.name,
        columns=tuple(
            ColumnPair(
                source_column_id=pair.source_column_id,
                target_column_id=pair.target_column_id,
            )
            for pair in body.columns
        ),
        source_cardinality=body.source_cardinality,
        target_cardinality=body.target_cardinality,
        on_delete=body.on_delete,
        on_update=body.on_update,
        waypoints=tuple(body.waypoints),
    )


def index_response(index: DiagramIndex) -> IndexResponseModel:
    return IndexResponseModel(
        id=index.id,
        table_id=index.table_id,
        name=index.name,
        type=index.type,
        columns=[
            IndexColumnModel(
                column_id=column.column_id,
                sort_order=column.sort_order,
                position=column.position,
            )
            for column in index.columns
        ],
        method=index.method,
        where=index.where,
        author_id=index.author_id,
        created_at=index.created_at,
        updated_at=index.updated_at,
    )


def relationship_response(relationship: Relationship) -> RelationshipResponseModel:
    return RelationshipResponseModel(
        id=relationship.id,
        database_id=relationship.database_id,
        name=relationship.name,
        source_table_id=relationship.source_table_id,
        target_table_id=relationship.target_table_id,
        columns=[
            RelationshipColumnPair(
                source_column_id=pair.source_column_id,
                target_column_id=pair.target_column_id,
            )
            for pair in relationship.columns
        ],
        source_cardinality=relationship.source_cardinality,
        target_cardinality=relationship.target_cardinality,
        on_delete=relationship.on_delete,
        on_update=relationship.on_update,
        waypoints=list(relationship.waypoints),
        author_id=relationship.author_id,
        created_at=relationship.created_at,
        updated_at=relationship.updated_at,
    )


@router.get("/indexes/", response_model=list[IndexResponseModel])
async def list_indexes(
    table_id: UUID, uow: SchemaUow, authorization: Authorization
) -> list[IndexResponseModel]:
    indexes = await ListIndexes(uow, authorization).execute(table_id)
    return [index_response(index) for index in indexes]


@router.get("/indexes/{index_id}", response_model=IndexResponseModel)
async def get_index(
    index_id: UUID, uow: SchemaUow, authorization: Authorization
) -> IndexResponseModel:
    return index_response(await GetIndex(uow, authorization).execute(index_id))


@router.post("/indexes/", response_model=IndexResponseModel, status_code=status.HTTP_201_CREATED)
async def create_index(
    request: Request,
    body: IndexCreateModel,
    uow: SchemaUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> IndexResponseModel:
    index = await CreateIndex(uow, authorization).execute(
        CreateIndexRequest(
            table_id=body.table_id,
            attributes=index_attributes(body),
            author_id=user.account_id,
        )
    )
    request.state.audit_resource_id = str(index.id)
    return index_response(index)


@router.put("/indexes/{index_id}", response_model=IndexResponseModel)
async def update_index(
    index_id: UUID,
    body: IndexUpdateModel,
    uow: SchemaUow,
    authorization: Authorization,
) -> IndexResponseModel:
    index = await UpdateIndex(uow, authorization).execute(
        UpdateIndexRequest(index_id=index_id, attributes=index_attributes(body))
    )
    return index_response(index)


@router.delete("/indexes/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index(index_id: UUID, uow: SchemaUow, authorization: Authorization) -> Response:
    await DeleteIndex(uow, authorization).execute(index_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/relationships/", response_model=list[RelationshipResponseModel])
async def list_relationships(
    database_id: UUID,
    uow: SchemaUow,
    authorization: Authorization,
) -> list[RelationshipResponseModel]:
    relationships = await ListRelationships(uow, authorization).execute(database_id)
    return [relationship_response(relationship) for relationship in relationships]


@router.get("/relationships/{relationship_id}", response_model=RelationshipResponseModel)
async def get_relationship(
    relationship_id: UUID,
    uow: SchemaUow,
    authorization: Authorization,
) -> RelationshipResponseModel:
    relationship = await GetRelationship(uow, authorization).execute(relationship_id)
    return relationship_response(relationship)


@router.post(
    "/relationships/",
    response_model=RelationshipResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    request: Request,
    body: RelationshipCreateModel,
    uow: SchemaUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> RelationshipResponseModel:
    relationship = await CreateRelationship(uow, authorization).execute(
        CreateRelationshipRequest(
            database_id=body.database_id,
            source_table_id=body.source_table_id,
            target_table_id=body.target_table_id,
            attributes=relationship_attributes(body),
            author_id=user.account_id,
        )
    )
    request.state.audit_resource_id = str(relationship.id)
    return relationship_response(relationship)


@router.put(
    "/relationships/{relationship_id}",
    response_model=RelationshipResponseModel,
)
async def update_relationship(
    relationship_id: UUID,
    body: RelationshipUpdateModel,
    uow: SchemaUow,
    authorization: Authorization,
) -> RelationshipResponseModel:
    relationship = await UpdateRelationship(uow, authorization).execute(
        UpdateRelationshipRequest(
            relationship_id=relationship_id,
            attributes=relationship_attributes(body),
        )
    )
    return relationship_response(relationship)


@router.delete(
    "/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_relationship(
    relationship_id: UUID,
    uow: SchemaUow,
    authorization: Authorization,
) -> Response:
    await DeleteRelationship(uow, authorization).execute(relationship_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
