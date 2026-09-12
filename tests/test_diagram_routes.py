from wdl_shared.schemas.engine.enums import ColumnType, DataBaseName, RealmVisibility

from wdl_be_core.main import create_app
from wdl_be_core.presentation.api.routers.enums import get_enum_catalog

EXPECTED_DIAGRAM_ROUTES = {
    "/canvas/{database_id}",
    "/canvas/{database_id}/groups",
    "/canvas/{database_id}/groups/{group_id}",
    "/canvas/{database_id}/notes",
    "/canvas/{database_id}/notes/{note_id}",
    "/columns/",
    "/columns/{column_id}",
    "/databases/",
    "/databases/{database_id}",
    "/indexes/",
    "/indexes/{index_id}",
    "/metadata/enums",
    "/projects/",
    "/projects/{project_id}",
    "/relationships/",
    "/relationships/{relationship_id}",
    "/tables/",
    "/tables/{table_id}",
}

EXPECTED_TAGS = {
    "canvas",
    "database relationships",
    "database schema",
    "projects",
    "realms",
    "system",
}


def test_diagram_routes_are_exposed_in_openapi() -> None:
    paths = create_app().openapi()["paths"]

    assert EXPECTED_DIAGRAM_ROUTES <= paths.keys()


def test_crud_routes_expose_expected_methods() -> None:
    paths = create_app().openapi()["paths"]

    for collection in (
        "/columns/",
        "/databases/",
        "/indexes/",
        "/projects/",
        "/relationships/",
        "/tables/",
    ):
        assert {"get", "post"} <= paths[collection].keys()

    for resource in (
        "/columns/{column_id}",
        "/databases/{database_id}",
        "/indexes/{index_id}",
        "/projects/{project_id}",
        "/relationships/{relationship_id}",
        "/tables/{table_id}",
    ):
        assert {"delete", "get", "put"} <= paths[resource].keys()


def test_column_update_contract_exposes_all_mutable_fields() -> None:
    schema = create_app().openapi()
    request_schema = schema["components"]["schemas"]["ColumnUpdateModel"]

    assert set(request_schema["properties"]) == {
        "array_dimensions",
        "auto_increment",
        "check",
        "custom_type",
        "default",
        "enum_values",
        "length",
        "name",
        "notice",
        "nullable",
        "precision",
        "primary_key",
        "scale",
        "sort_order",
        "type",
        "unique",
        "unsigned",
    }
    assert "table_id" not in request_schema["properties"]
    assert "author_id" not in request_schema["properties"]


def test_enum_catalog_contract_contains_every_domain_enum() -> None:
    schema = create_app().openapi()
    response_schema = schema["components"]["schemas"]["EnumCatalogResponseModel"]

    assert set(response_schema["properties"]) == {
        "column_types",
        "database_types",
        "index_types",
        "realm_statuses",
        "realm_visibilities",
        "referential_actions",
        "relationship_cardinalities",
        "sort_orders",
    }


async def test_enum_catalog_values_come_from_shared_domain_enums() -> None:
    catalog = await get_enum_catalog()

    assert catalog.database_types == [item.value for item in DataBaseName]
    assert catalog.column_types == [item.value for item in ColumnType]
    assert catalog.realm_visibilities == [item.value for item in RealmVisibility]


def test_all_used_tags_have_openapi_descriptions() -> None:
    schema = create_app().openapi()
    tags   = schema["tags"]

    assert {tag["name"] for tag in tags} == EXPECTED_TAGS
    assert all(tag["description"].strip() for tag in tags)
