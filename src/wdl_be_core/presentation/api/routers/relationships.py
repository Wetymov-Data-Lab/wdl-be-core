from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
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

from wdl_be_core.domain.exceptions import EntityNotFoundError
from wdl_be_core.infrastructure.database.models.database import (
    Columns,
    Databases,
    DiagramIndexColumns,
    DiagramIndexes,
    RelationshipColumns,
    Relationships,
    Tables,
)
from wdl_be_core.presentation.api.dependencies.database import get_database_session
from wdl_be_core.presentation.api.routers.crud import (
    apply_values,
    commit_or_conflict,
    flush_or_conflict,
    get_or_404,
)

router = APIRouter(tags=["database relationships"])
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


async def index_response(session: AsyncSession, index: DiagramIndexes) -> IndexResponseModel:
    columns = (
        await session.scalars(
            select(DiagramIndexColumns)
            .where(DiagramIndexColumns.index_id == index.id)
            .order_by(DiagramIndexColumns.position)
        )
    ).all()
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
            for column in columns
        ],
        method=index.method,
        where=index.where,
        author_id=index.author_id,
        created_at=index.created_at,
        updated_at=index.updated_at,
    )


async def relationship_response(
    session: AsyncSession,
    relationship: Relationships,
) -> RelationshipResponseModel:
    columns = (
        await session.scalars(
            select(RelationshipColumns).where(
                RelationshipColumns.relationship_id == relationship.id
            )
        )
    ).all()
    return RelationshipResponseModel(
        id=relationship.id,
        database_id=relationship.database_id,
        name=relationship.name,
        source_table_id=relationship.source_table_id,
        target_table_id=relationship.target_table_id,
        columns=[
            RelationshipColumnPair(
                source_column_id=column.source_column_id,
                target_column_id=column.target_column_id,
            )
            for column in columns
        ],
        source_cardinality=relationship.source_cardinality,
        target_cardinality=relationship.target_cardinality,
        on_delete=relationship.on_delete,
        on_update=relationship.on_update,
        waypoints=relationship.waypoints,
        author_id=relationship.author_id,
        created_at=relationship.created_at,
        updated_at=relationship.updated_at,
    )


@router.get("/indexes/", response_model=list[IndexResponseModel])
async def list_indexes(table_id: UUID, session: DatabaseSession) -> list[IndexResponseModel]:
    indexes = (
        await session.scalars(
            select(DiagramIndexes)
            .where(DiagramIndexes.table_id == table_id)
            .order_by(DiagramIndexes.created_at)
        )
    ).all()
    return [await index_response(session, index) for index in indexes]


@router.get("/indexes/{index_id}", response_model=IndexResponseModel)
async def get_index(index_id: UUID, session: DatabaseSession) -> IndexResponseModel:
    index = await get_or_404(session, DiagramIndexes, index_id)
    return await index_response(session, index)


@router.post("/indexes/", response_model=IndexResponseModel, status_code=status.HTTP_201_CREATED)
async def create_index(body: IndexCreateModel, session: DatabaseSession) -> IndexResponseModel:
    await get_or_404(session, Tables, body.table_id)
    for column_item in body.columns:
        column = await get_or_404(session, Columns, column_item.column_id)
        if column.table_id != body.table_id:
            raise EntityNotFoundError(
                f"Column {column.id} does not belong to table {body.table_id}"
            )
    index = DiagramIndexes(
        id=uuid4(),
        **body.model_dump(exclude={"columns"}),
    )
    session.add(index)
    await flush_or_conflict(session, f"Index '{body.name}' already exists")
    session.add_all(
        DiagramIndexColumns(
            id=uuid4(),
            index_id=index.id,
            **column.model_dump(),
        )
        for column in body.columns
    )
    await commit_or_conflict(session, "Index contains duplicate columns or positions")
    await session.refresh(index)
    return await index_response(session, index)


@router.put("/indexes/{index_id}", response_model=IndexResponseModel)
async def update_index(
    index_id: UUID,
    body: IndexUpdateModel,
    session: DatabaseSession,
) -> IndexResponseModel:
    index = await get_or_404(session, DiagramIndexes, index_id)
    for column_item in body.columns:
        column = await get_or_404(session, Columns, column_item.column_id)
        if column.table_id != index.table_id:
            raise EntityNotFoundError(
                f"Column {column.id} does not belong to table {index.table_id}"
            )
    apply_values(index, body.model_dump(exclude={"columns"}))
    await session.execute(
        delete(DiagramIndexColumns).where(DiagramIndexColumns.index_id == index.id)
    )
    await session.flush()
    session.add_all(
        DiagramIndexColumns(
            id=uuid4(),
            index_id=index.id,
            **column.model_dump(),
        )
        for column in body.columns
    )
    await commit_or_conflict(session, "Index contains duplicate columns or positions")
    await session.refresh(index)
    return await index_response(session, index)


@router.delete("/indexes/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index(index_id: UUID, session: DatabaseSession) -> Response:
    index = await get_or_404(session, DiagramIndexes, index_id)
    await session.delete(index)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/relationships/", response_model=list[RelationshipResponseModel])
async def list_relationships(
    database_id: UUID,
    session: DatabaseSession,
) -> list[RelationshipResponseModel]:
    relationships = (
        await session.scalars(
            select(Relationships)
            .where(Relationships.database_id == database_id)
            .order_by(Relationships.created_at)
        )
    ).all()
    return [
        await relationship_response(session, relationship) for relationship in relationships
    ]


@router.get("/relationships/{relationship_id}", response_model=RelationshipResponseModel)
async def get_relationship(
    relationship_id: UUID,
    session: DatabaseSession,
) -> RelationshipResponseModel:
    relationship = await get_or_404(session, Relationships, relationship_id)
    return await relationship_response(session, relationship)


@router.post(
    "/relationships/",
    response_model=RelationshipResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    body: RelationshipCreateModel,
    session: DatabaseSession,
) -> RelationshipResponseModel:
    await get_or_404(session, Databases, body.database_id)
    source_table = await get_or_404(session, Tables, body.source_table_id)
    target_table = await get_or_404(session, Tables, body.target_table_id)
    if source_table.database_id != body.database_id or target_table.database_id != body.database_id:
        raise EntityNotFoundError("Relationship tables must belong to the requested database")
    for column_pair in body.columns:
        source_column = await get_or_404(session, Columns, column_pair.source_column_id)
        target_column = await get_or_404(session, Columns, column_pair.target_column_id)
        if (
            source_column.table_id != body.source_table_id
            or target_column.table_id != body.target_table_id
        ):
            raise EntityNotFoundError("Relationship columns must belong to their endpoint tables")
    relationship = Relationships(
        id=uuid4(),
        **body.model_dump(exclude={"columns"}),
    )
    session.add(relationship)
    await flush_or_conflict(session, f"Relationship '{body.name}' already exists")
    session.add_all(
        RelationshipColumns(
            id=uuid4(),
            relationship_id=relationship.id,
            **column.model_dump(),
        )
        for column in body.columns
    )
    await commit_or_conflict(session, "Relationship contains duplicate column mappings")
    await session.refresh(relationship)
    return await relationship_response(session, relationship)


@router.put(
    "/relationships/{relationship_id}",
    response_model=RelationshipResponseModel,
)
async def update_relationship(
    relationship_id: UUID,
    body: RelationshipUpdateModel,
    session: DatabaseSession,
) -> RelationshipResponseModel:
    relationship = await get_or_404(session, Relationships, relationship_id)
    for column_pair in body.columns:
        source_column = await get_or_404(session, Columns, column_pair.source_column_id)
        target_column = await get_or_404(session, Columns, column_pair.target_column_id)
        if (
            source_column.table_id != relationship.source_table_id
            or target_column.table_id != relationship.target_table_id
        ):
            raise EntityNotFoundError("Relationship columns must belong to their endpoint tables")
    apply_values(relationship, body.model_dump(exclude={"columns"}))
    await session.execute(
        delete(RelationshipColumns).where(
            RelationshipColumns.relationship_id == relationship.id
        )
    )
    await session.flush()
    session.add_all(
        RelationshipColumns(
            id=uuid4(),
            relationship_id=relationship.id,
            **column.model_dump(),
        )
        for column in body.columns
    )
    await commit_or_conflict(session, "Relationship contains duplicate column mappings")
    await session.refresh(relationship)
    return await relationship_response(session, relationship)


@router.delete(
    "/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_relationship(
    relationship_id: UUID,
    session: DatabaseSession,
) -> Response:
    relationship = await get_or_404(session, Relationships, relationship_id)
    await session.delete(relationship)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
