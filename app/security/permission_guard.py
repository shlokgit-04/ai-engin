from abc import ABC, abstractmethod

from app.orchestrator.context import ExecutionContext
from app.document_intelligence.metadata.models import DocumentMetadata


class PermissionGuard(ABC):
    @abstractmethod
    async def can_access_document(
        self,
        user_context: ExecutionContext,
        document: DocumentMetadata,
    ) -> bool:
        ...
