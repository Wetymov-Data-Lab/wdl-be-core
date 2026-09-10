from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.schema import CreateTable

from common.transaction_manager import (
    AuditEntry,
    AuditLog,
    OutboxEvent,
    OutboxMessage,
    TransactionManager,
    TransactionManagerBase,
    mask_sensitive_data,
)


def test_transaction_models_compile_and_mask_nested_secrets() -> None:
    dialect = postgresql.dialect()
    assert set(TransactionManagerBase.metadata.tables) == {"audit_log", "outbox"}
    for table in TransactionManagerBase.metadata.sorted_tables:
        assert f"CREATE TABLE {table.name}" in str(CreateTable(table).compile(dialect=dialect))
    assert mask_sensitive_data({"nested": {"password": "secret"}}) == {
        "nested": {"password": "***"}
    }


@pytest.mark.asyncio
async def test_run_persists_audit_and_outbox_in_one_transaction() -> None:
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    session.begin.return_value = transaction
    factory = cast(async_sessionmaker[AsyncSession], MagicMock(return_value=session))
    manager = TransactionManager(factory, service_name="wdl-be-core")
    resource_id = uuid4()

    async def operation(active_session: AsyncSession) -> dict[str, str]:
        assert active_session is session
        return {"id": str(resource_id)}

    result = await manager.run(
        operation,
        audit=AuditEntry("resource.create", "resource", resource_id, input={"token": "secret"}),
        outbox=lambda created: OutboxEvent("resources", "resource.created", created),
    )
    assert result["id"] == str(resource_id)
    assert cast(AuditLog, session.add.call_args.args[0]).input == {"token": "***"}
    messages = list(session.add_all.call_args.args[0])
    assert all(isinstance(message, OutboxMessage) for message in messages)
    assert {message.event_type for message in messages} == {"resource.created", "audit_log.created"}
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_transaction_context_commits_request_audit_with_managed_writes() -> None:
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    session.begin.return_value = transaction
    factory = cast(async_sessionmaker[AsyncSession], MagicMock(return_value=session))
    manager = TransactionManager(factory, service_name="wdl-be-core")

    async with manager.transaction(
        audit=lambda: AuditEntry("realm.create", "realm", actor_id=uuid4())
    ) as active_session:
        assert active_session is session

    staged = [call.args[0] for call in session.add.call_args_list]
    assert any(isinstance(item, AuditLog) for item in staged)
    assert any(isinstance(item, OutboxMessage) for item in staged)
    session.flush.assert_awaited_once()
