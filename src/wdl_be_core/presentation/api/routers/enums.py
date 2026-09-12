from enum import StrEnum

from fastapi import APIRouter, Depends
from wdl_shared.schemas.engine.enums import (
    ColumnType,
    DataBaseName,
    IndexType,
    RealmStatus,
    RealmVisibility,
    ReferentialAction,
    RelationshipCardinality,
    SortOrder,
)

from wdl_be_core.presentation.api.dependencies.authentication import get_current_user
from wdl_be_core.presentation.api.schemas.enums import EnumCatalogResponseModel

router = APIRouter(
    prefix="/metadata",
    tags=["database schema"],
    dependencies=[Depends(get_current_user)],
)


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_type]


@router.get("/enums", response_model=EnumCatalogResponseModel)
async def get_enum_catalog() -> EnumCatalogResponseModel:
    """Return the authoritative enum catalog used by schemas and domain models."""

    return EnumCatalogResponseModel(
        database_types=enum_values(DataBaseName),
        column_types=enum_values(ColumnType),
        index_types=enum_values(IndexType),
        sort_orders=enum_values(SortOrder),
        referential_actions=enum_values(ReferentialAction),
        relationship_cardinalities=enum_values(RelationshipCardinality),
        realm_statuses=enum_values(RealmStatus),
        realm_visibilities=enum_values(RealmVisibility),
    )
