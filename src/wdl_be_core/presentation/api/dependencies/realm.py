from wdl_be_core.infrastructure.database.session import async_session_factory
from wdl_be_core.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def get_realm_uow() -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(async_session_factory)
