from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from wdl_be_core.application.authorization import AuthorizationService
from wdl_be_core.domain.exceptions import EntityNotFoundError


def test_owned_resource_queries_include_realm_boundary() -> None:
    service = AuthorizationService(AsyncMock(), uuid4())

    project_sql = str(service.projects())
    database_sql = str(service.databases())

    assert "JOIN realms" in project_sql
    assert "realms.author_id" in project_sql
    assert "realms.status" in project_sql
    assert "JOIN realms" in database_sql
    assert "realms.author_id" in database_sql


async def test_inaccessible_resource_is_hidden_as_not_found() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    service = AuthorizationService(session, uuid4())

    with pytest.raises(EntityNotFoundError):
        await service.require_database(uuid4())
