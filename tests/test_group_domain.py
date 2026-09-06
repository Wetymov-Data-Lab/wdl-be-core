from datetime import UTC, datetime
from uuid import uuid4

import pytest

from wdl_be_core.domain.entities.group import DiagramGroup
from wdl_be_core.domain.exceptions import AuthorizationError, DomainError


def make_group() -> DiagramGroup:
    return DiagramGroup.create(
        database_id=uuid4(),
        name="  Backend  ",
        x=10,
        y=20,
        width=300,
        height=180,
        color="#aabbcc",
        is_collapsed=False,
        table_ids=[uuid4()],
        author_id=uuid4(),
        created_at=datetime.now(UTC),
    )


def test_group_normalizes_visual_values() -> None:
    group = make_group()

    assert group.name.value == "Backend"
    assert group.color is not None
    assert group.color.value == "#AABBCC"


def test_group_rejects_invalid_area_and_duplicate_members() -> None:
    group = make_group()

    with pytest.raises(DomainError):
        DiagramGroup.create(
            database_id=group.database_id,
            name="Invalid",
            x=0,
            y=0,
            width=0,
            height=100,
            color=None,
            is_collapsed=False,
            table_ids=[],
            author_id=group.author_id,
            created_at=datetime.now(UTC),
        )

    table_id = uuid4()
    with pytest.raises(DomainError):
        DiagramGroup.create(
            database_id=group.database_id,
            name="Duplicate tables",
            x=0,
            y=0,
            width=100,
            height=100,
            color=None,
            is_collapsed=False,
            table_ids=[table_id, table_id],
            author_id=group.author_id,
            created_at=datetime.now(UTC),
        )


def test_only_group_author_can_change_it() -> None:
    group = make_group()

    with pytest.raises(AuthorizationError):
        group.update(
            name="Changed",
            x=0,
            y=0,
            width=100,
            height=100,
            color=None,
            is_collapsed=False,
            table_ids=[],
            updated_by=uuid4(),
            updated_at=datetime.now(UTC),
        )
