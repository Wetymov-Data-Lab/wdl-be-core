from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from common.exceptions.exceptions import EntityAlreadyExistsError
from context.infrastructure.repositories.canvas_state import CanvasStateRepository
from context.infrastructure.repositories.canvas_state_contract import CanvasStateUnitOfWork
from context.infrastructure.repositories.column import ColumnRepository
from context.infrastructure.repositories.database import DatabaseRepository
from context.infrastructure.repositories.group import GroupRepository
from context.infrastructure.repositories.group_contract import GroupUnitOfWork
from context.infrastructure.repositories.index import IndexRepository
from context.infrastructure.repositories.note import NoteRepository
from context.infrastructure.repositories.note_contract import NoteUnitOfWork
from context.infrastructure.repositories.project import ProjectRepository
from context.infrastructure.repositories.project_contract import ProjectUnitOfWork
from context.infrastructure.repositories.realm import RealmRepository
from context.infrastructure.repositories.realm_contract import RealmUnitOfWork
from context.infrastructure.repositories.relationship import RelationshipRepository
from context.infrastructure.repositories.sql_export_contract import SqlExportUnitOfWork
from context.infrastructure.repositories.table import TableRepository


class SQLAlchemyUnitOfWork(
    RealmUnitOfWork,
    GroupUnitOfWork,
    ProjectUnitOfWork,
    SqlExportUnitOfWork,
    CanvasStateUnitOfWork,
    NoteUnitOfWork,
):
    """Base SQLAlchemy transaction; domain repositories are added by subclasses."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        managed_session: AsyncSession | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._managed_session = managed_session
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._managed_session or self._session_factory()
        self.realms = RealmRepository(self.session)
        self.groups = GroupRepository(self.session)
        self.projects = ProjectRepository(self.session)
        self.databases = DatabaseRepository(self.session)
        self.tables = TableRepository(self.session)
        self.columns = ColumnRepository(self.session)
        self.indexes = IndexRepository(self.session)
        self.relationships = RelationshipRepository(self.session)
        self.canvas_states = CanvasStateRepository(self.session)
        self.notes = NoteRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        try:
            if self._managed_session is None:
                await self.rollback()
        finally:
            if self._managed_session is None:
                await self.session.close()
            self.session = None

    async def commit(self) -> None:
        try:
            if self._managed_session is None:
                await self._get_session().commit()
            else:
                await self._get_session().flush()
        except IntegrityError as error:
            raise EntityAlreadyExistsError("Entity violates a uniqueness constraint") from error

    async def rollback(self) -> None:
        if self._managed_session is None:
            await self._get_session().rollback()

    def _get_session(self) -> AsyncSession:
        if self.session is None:
            raise RuntimeError("Unit of work must be used as an async context manager")
        return self.session
