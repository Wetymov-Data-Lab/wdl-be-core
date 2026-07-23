from wdl_be_core.main import create_app

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


def test_all_used_tags_have_openapi_descriptions() -> None:
    schema = create_app().openapi()
    tags   = schema["tags"]

    assert {tag["name"] for tag in tags} == EXPECTED_TAGS
    assert all(tag["description"].strip() for tag in tags)
