from abc import ABC, abstractmethod


class UseCase[RequestT, ResponseT](ABC):
    """Application operation with a single request and response contract."""

    @abstractmethod
    async def execute(self, request: RequestT) -> ResponseT:
        """Execute the application scenario."""
