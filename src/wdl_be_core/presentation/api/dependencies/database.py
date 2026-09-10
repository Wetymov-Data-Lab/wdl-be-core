from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.transaction_manager import TransactionManager
from wdl_be_core.infrastructure.database.session import async_session_factory
from wdl_be_core.presentation.api.dependencies.transactions import request_audit_entry


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one manager-owned transaction and audit boundary per request."""
    manager = TransactionManager(async_session_factory, service_name="wdl-be-core")
    async with manager.transaction(audit=lambda: request_audit_entry(request)) as session:
        yield session
