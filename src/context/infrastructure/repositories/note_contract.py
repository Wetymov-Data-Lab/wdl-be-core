from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.note import DiagramNote


class NoteRepository(Repository[DiagramNote, UUID]):
    @abstractmethod
    async def list(self, database_id: UUID) -> list[DiagramNote]: ...

    @abstractmethod
    async def save(self, note: DiagramNote) -> None: ...


class NoteUnitOfWork(UnitOfWork):
    notes: NoteRepository
