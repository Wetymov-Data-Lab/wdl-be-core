from pydantic import BaseModel


class EnumCatalogResponseModel(BaseModel):
    """Enum values supported by the Core API contracts."""

    database_types: list[str]
    column_types: list[str]
    index_types: list[str]
    sort_orders: list[str]
    referential_actions: list[str]
    relationship_cardinalities: list[str]
    realm_statuses: list[str]
    realm_visibilities: list[str]
