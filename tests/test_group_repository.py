from typing import cast
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession
from test_group_domain import make_group

from context.infrastructure.repositories.group import GroupRepository
from context.infrastructure.schemas.canvas import DiagramGroups, DiagramGroupTables


async def test_group_row_is_flushed_before_its_memberships() -> None:
    session = Mock(spec=AsyncSession)
    session.flush = AsyncMock()
    group = make_group()

    await GroupRepository(cast(AsyncSession, session)).add(group)

    calls = [name for name, *_ in session.mock_calls]
    assert calls == ["add", "flush", "add_all"]
    assert isinstance(session.add.call_args.args[0], DiagramGroups)
    (membership,) = list(session.add_all.call_args.args[0])
    assert isinstance(membership, DiagramGroupTables)
    assert (membership.group_id, membership.table_id) == (group.id, group.table_ids[0])
