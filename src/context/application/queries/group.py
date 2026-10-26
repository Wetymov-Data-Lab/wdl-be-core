from uuid import UUID

from context.application.use_case import UseCase
from context.domain.entities.group import DiagramGroup
from context.infrastructure.repositories.group_contract import GroupUnitOfWork


class ListGroups(UseCase[UUID, list[DiagramGroup]]):
    def __init__(self, uow: GroupUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: UUID) -> list[DiagramGroup]:
        async with self._uow:
            return await self._uow.groups.list(request)
