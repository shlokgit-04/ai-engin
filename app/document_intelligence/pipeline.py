from app.document_intelligence.interfaces import BaseDocumentIntelligencePipeline
from app.orchestrator.context import ExecutionContext
from app.core.logging import logger


class DocumentIntelligencePipeline(BaseDocumentIntelligencePipeline):
    async def execute(self, context: ExecutionContext) -> str:
        logger.info("Document Intelligence pipeline invoked", message_length=len(context.message))
        return "Document Intelligence Pipeline not implemented yet."
