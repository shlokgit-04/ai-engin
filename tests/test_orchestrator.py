import pytest
from app.orchestrator.classifier import Classifier
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.orchestrator import AIOrchestrator
from app.orchestrator.pipeline import ExecutionPipeline, FEATURE_PLACEHOLDER
from app.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.models.base import BaseLLM


def make_context(message: str) -> ExecutionContext:
    return ExecutionContext(message=message)


class RecordingLLM(BaseLLM):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[str] = []

    async def generate_response(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        return f"{self.name}:{prompt}"

    async def health_check(self) -> bool:
        return True

    @property
    def was_called(self) -> bool:
        return len(self.calls) > 0


@pytest.fixture
def gemini() -> RecordingLLM:
    return RecordingLLM("gemini")


@pytest.fixture
def ollama() -> RecordingLLM:
    return RecordingLLM("ollama")


@pytest.fixture
def knowledge() -> DocumentIntelligencePipeline:
    return DocumentIntelligencePipeline()


@pytest.fixture
def pipeline(
    gemini: RecordingLLM,
    ollama: RecordingLLM,
    knowledge: DocumentIntelligencePipeline,
) -> ExecutionPipeline:
    return ExecutionPipeline(gemini=gemini, ollama=ollama, knowledge_pipeline=knowledge)


@pytest.fixture
def orchestrator(pipeline: ExecutionPipeline) -> AIOrchestrator:
    return AIOrchestrator(pipeline=pipeline)


class TestClassification:
    classifier = Classifier()

    def test_general_chat(self):
        assert self.classifier.classify("Explain Python") == RequestCategory.GENERAL_CHAT
        assert self.classifier.classify("What is FastAPI") == RequestCategory.GENERAL_CHAT
        assert self.classifier.classify("Write an email") == RequestCategory.GENERAL_CHAT
        assert self.classifier.classify("Hello") == RequestCategory.GENERAL_CHAT
        assert self.classifier.classify("How do I write a function") == RequestCategory.GENERAL_CHAT

    def test_company_knowledge(self):
        assert self.classifier.classify("Nurofin") == RequestCategory.COMPANY_KNOWLEDGE
        assert self.classifier.classify("What is the vendor policy") == RequestCategory.COMPANY_KNOWLEDGE
        assert self.classifier.classify("Project status report") == RequestCategory.COMPANY_KNOWLEDGE
        assert self.classifier.classify("Employee headcount") == RequestCategory.COMPANY_KNOWLEDGE
        assert self.classifier.classify("Finance quarterly report") == RequestCategory.COMPANY_KNOWLEDGE
        assert self.classifier.classify("Customer agreement") == RequestCategory.COMPANY_KNOWLEDGE
        assert self.classifier.classify("Proposal for new client") == RequestCategory.COMPANY_KNOWLEDGE
        assert self.classifier.classify("Internal policy update") == RequestCategory.COMPANY_KNOWLEDGE

    def test_document_query(self):
        assert self.classifier.classify("Summarize this PDF") == RequestCategory.DOCUMENT_QUERY
        assert self.classifier.classify("Search document for terms") == RequestCategory.DOCUMENT_QUERY
        assert self.classifier.classify("Find contract in document") == RequestCategory.DOCUMENT_QUERY
        assert self.classifier.classify("Summarise the report") == RequestCategory.DOCUMENT_QUERY

    def test_document_upload(self):
        assert self.classifier.classify("upload this pdf") == RequestCategory.DOCUMENT_UPLOAD
        assert self.classifier.classify("Upload document") == RequestCategory.DOCUMENT_UPLOAD
        assert self.classifier.classify("Attach file report.docx") == RequestCategory.DOCUMENT_UPLOAD
        assert self.classifier.classify("Convert this docx") == RequestCategory.DOCUMENT_UPLOAD

    def test_image_analysis(self):
        assert self.classifier.classify("Analyze image.png") == RequestCategory.IMAGE_ANALYSIS
        assert self.classifier.classify("Process this picture") == RequestCategory.IMAGE_ANALYSIS
        assert self.classifier.classify("Upload photo for analysis") == RequestCategory.IMAGE_ANALYSIS
        assert self.classifier.classify("Analyze image.jpg") == RequestCategory.IMAGE_ANALYSIS

    def test_meeting(self):
        assert self.classifier.classify("Create meeting minutes") == RequestCategory.MEETING
        assert self.classifier.classify("Generate MoM") == RequestCategory.MEETING
        assert self.classifier.classify("meeting transcript") == RequestCategory.MEETING
        assert self.classifier.classify("Review the agenda") == RequestCategory.MEETING

    def test_document_query_beats_file_format(self):
        assert self.classifier.classify("Summarize this PDF") == RequestCategory.DOCUMENT_QUERY

    def test_document_query_beats_meeting_keyword(self):
        assert self.classifier.classify("Summarize the meeting") == RequestCategory.DOCUMENT_QUERY

    def test_task_assistant(self):
        assert self.classifier.classify("Create a task") == RequestCategory.TASK_ASSISTANT
        assert self.classifier.classify("Set a deadline") == RequestCategory.TASK_ASSISTANT
        assert self.classifier.classify("Set a reminder") == RequestCategory.TASK_ASSISTANT
        assert self.classifier.classify("Follow-up on project") == RequestCategory.TASK_ASSISTANT

    def test_company_takes_precedence_over_general(self):
        assert self.classifier.classify("Tell me about Nurofin") == RequestCategory.COMPANY_KNOWLEDGE

    def test_upload_beats_company(self):
        assert self.classifier.classify("Upload the proposal pdf") == RequestCategory.DOCUMENT_UPLOAD

    def test_document_query_beats_meeting(self):
        assert self.classifier.classify("Summarize meeting transcript") == RequestCategory.DOCUMENT_QUERY

    def test_upload_beats_task(self):
        assert self.classifier.classify("Upload the task list pdf") == RequestCategory.DOCUMENT_UPLOAD


class TestRouting:
    @pytest.mark.asyncio
    async def test_general_chat_routes_to_gemini(
        self, orchestrator: AIOrchestrator, gemini: RecordingLLM, ollama: RecordingLLM
    ):
        result = await orchestrator.route_request(make_context("Explain Python"))
        assert gemini.was_called
        assert not ollama.was_called
        assert result == "gemini:Explain Python"

    @pytest.mark.asyncio
    async def test_company_knowledge_routes_to_knowledge_pipeline(
        self, orchestrator: AIOrchestrator, gemini: RecordingLLM, ollama: RecordingLLM
    ):
        result = await orchestrator.route_request(make_context("Nurofin revenue"))
        assert not gemini.was_called
        assert not ollama.was_called
        assert result == "Document Intelligence Pipeline not implemented yet."

    @pytest.mark.asyncio
    async def test_document_query_routes_to_knowledge_pipeline(
        self, orchestrator: AIOrchestrator, gemini: RecordingLLM, ollama: RecordingLLM
    ):
        result = await orchestrator.route_request(make_context("Summarize this PDF"))
        assert not gemini.was_called
        assert not ollama.was_called
        assert result == "Document Intelligence Pipeline not implemented yet."

    @pytest.mark.asyncio
    async def test_image_analysis_placeholder(
        self, orchestrator: AIOrchestrator, gemini: RecordingLLM, ollama: RecordingLLM
    ):
        result = await orchestrator.route_request(make_context("Analyze image.png"))
        assert result == FEATURE_PLACEHOLDER
        assert not gemini.was_called
        assert not ollama.was_called

    @pytest.mark.asyncio
    async def test_meeting_placeholder(
        self, orchestrator: AIOrchestrator, gemini: RecordingLLM, ollama: RecordingLLM
    ):
        result = await orchestrator.route_request(make_context("Create meeting minutes"))
        assert result == FEATURE_PLACEHOLDER
        assert not gemini.was_called
        assert not ollama.was_called

    @pytest.mark.asyncio
    async def test_task_placeholder(
        self, orchestrator: AIOrchestrator, gemini: RecordingLLM, ollama: RecordingLLM
    ):
        result = await orchestrator.route_request(make_context("Create a task"))
        assert result == FEATURE_PLACEHOLDER
        assert not gemini.was_called
        assert not ollama.was_called

    @pytest.mark.asyncio
    async def test_document_upload_placeholder(
        self, orchestrator: AIOrchestrator, gemini: RecordingLLM, ollama: RecordingLLM
    ):
        result = await orchestrator.route_request(make_context("Upload this file.pdf"))
        assert result == FEATURE_PLACEHOLDER
        assert not gemini.was_called
        assert not ollama.was_called


class TestExecutionContext:
    def test_default_fields(self):
        ctx = ExecutionContext(message="Hello")
        assert ctx.message == "Hello"
        assert ctx.user_id is None
        assert ctx.department is None
        assert ctx.metadata == {}

    def test_rich_context(self):
        ctx = ExecutionContext(
            message="Test",
            user_id="user-1",
            role="admin",
            department="engineering",
            project_id="proj-42",
            session_id="sess-abc",
            metadata={"source": "slack"},
        )
        assert ctx.user_id == "user-1"
        assert ctx.department == "engineering"
        assert ctx.metadata["source"] == "slack"


class TestDocumentMetadata:
    from app.document_intelligence.metadata.models import DocumentMetadata
    from app.document_intelligence.metadata.classification import DocumentClassification

    def test_default_classification(self):
        meta = self.DocumentMetadata(document_id="doc-1", file_name="report.pdf")
        assert meta.confidentiality == self.DocumentClassification.INTERNAL

    def test_classification_override(self):
        meta = self.DocumentMetadata(
            document_id="doc-2",
            file_name="secret.pdf",
            confidentiality=self.DocumentClassification.HIGHLY_CONFIDENTIAL,
        )
        assert meta.confidentiality == self.DocumentClassification.HIGHLY_CONFIDENTIAL
