# Nurofin Executive AI Engine

AI microservice powering an enterprise operating system.

## Capabilities

- AI Chat
- Multi-model routing
- Document & image understanding
- RAG
- Meeting intelligence
- Minutes of Meeting generation
- Task extraction
- Executive recommendations
- Daily briefings
- Tool calling
- Chat memory

## Tech Stack

- Python 3.12+
- FastAPI
- Pydantic v2
- Google Gemini SDK / Ollama
- Qdrant
- structlog

## Getting Started

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Project Structure

```
app/
├── api/              HTTP endpoints (thin handlers)
├── agents/           Specialised AI agents
│   ├── base.py           BaseAgent (execute, health_check, supported_categories)
│   ├── chat_agent.py     ChatAgent (legacy entry point)
│   ├── knowledge_agent.py  KnowledgeAgent (GENERAL_CHAT, COMPANY_KNOWLEDGE, DOCUMENT_QUERY)
│   ├── planner_agent.py  PlannerAgent (DOCUMENT_UPLOAD, IMAGE_ANALYSIS — placeholder)
│   ├── finance_agent.py  FinanceAgent (FINANCE — placeholder)
│   ├── meeting_agent.py  MeetingAgent (MEETING — placeholder)
│   ├── task_agent.py     TaskAgent (TASK_ASSISTANT — placeholder)
│   ├── notification_agent.py  NotificationAgent (placeholder)
│   └── recommendation_agent.py  RecommendationAgent (RECOMMENDATION — placeholder)
├── core/             Config, logging, exceptions, DI
├── document_intelligence/  Document intelligence pipeline
│   ├── parsers/
│   │   ├── base.py       BaseParser interface
│   │   ├── pdf.py        PDF parser (placeholder)
│   │   ├── docx.py       DOCX parser (placeholder)
│   │   └── image.py      Image parser (placeholder)
│   ├── ocr/
│   │   └── base.py       OCR interface
│   ├── preprocessing/
│   │   ├── cleaner.py    Text cleaning interface
│   │   └── chunker.py    Chunking interface
│   ├── embeddings/
│   │   └── base.py       Embedding provider interface
│   ├── vectorstore/
│   │   └── base.py       Vector store interface
│   ├── retriever/
│   │   └── base.py       Retriever interface
│   ├── reranker/
│   │   └── base.py       BaseReranker interface (Cross Encoder, BGE future)
│   ├── context/
│   │   └── builder.py    Context assembly interface
│   ├── metadata/
│   │   ├── models.py     DocumentMetadata model
│   │   └── classification.py  DocumentClassification enum
│   ├── pipeline.py       DocumentIntelligencePipeline (placeholder)
│   └── interfaces.py     Abstract base interfaces
├── memory/           Multi-tier memory system
│   ├── base.py           BaseMemory (add, get, clear)
│   ├── manager.py        MemoryManager (remember, recall, forget, summarize)
│   ├── short_term.py     ShortTermMemory interface (TTL-based)
│   ├── long_term.py      LongTermMemory interface (persistent + search)
│   ├── conversation.py   ConversationMemory interface (session-based)
│   └── chat_memory.py    ChatMemory (in-memory implementation)
├── models/           AI model integrations (Gemini, Ollama)
├── orchestrator/     AI brain
│   ├── classifier.py     Rule-based request classifier
│   ├── context.py        ExecutionContext model
│   ├── enums.py          Request categories (+FINANCE, +RECOMMENDATION)
│   ├── orchestrator.py   AIOrchestrator (classify → select agent → execute)
│   └── pipeline.py       ExecutionPipeline (dispatch)
├── security/         Enterprise security
│   └── permission_guard.py  PermissionGuard interface (RBAC-ready)
├── prompts/          Prompt templates
├── rag/              Retrieval-Augmented Generation (future)
├── router/           Orchestration layer
├── schemas/          Pydantic request/response models
├── services/         Business logic
├── storage/          Storage backends
├── tools/            Tool/function calling
└── main.py           Application entry point
```

## Architecture

```
API Layer  →  Router  →  Services  →  AI Agents
                                          ↓
                                   AI Orchestrator
                                          ↓
                                 Specialised Agent
                                    ↓         ↓
                          Execution Pipeline  Document Intelligence
                                    ↓              ↓
                              Gemini/Ollama    Reranker → Context Builder → Permission Guard → Ollama
```

Each layer has a single responsibility. Routes validate and delegate. Services contain business logic. Agents encapsulate AI behaviour. The Orchestrator classifies the request, selects the appropriate Specialised Agent, and the agent executes the correct pipeline.

### Execution Context

Every request is encapsulated in `ExecutionContext`, a strongly-typed model carrying `message`, `user_id`, `role`, `department`, `project_id`, `session_id`, `conversation_history`, `uploaded_files`, and extensible `metadata`. All future handlers receive this context instead of raw strings.

### Execution Pipeline

The `ExecutionPipeline` dispatches based on `RequestCategory`. The orchestrator first selects a specialised agent, which then executes the appropriate pipeline:

| Category | Agent | Pipeline | Status |
|---|---|---|---|
| `GENERAL_CHAT` | KnowledgeAgent | Gemini | Active |
| `COMPANY_KNOWLEDGE` | KnowledgeAgent | Document Intelligence → Ollama | Placeholder |
| `DOCUMENT_QUERY` | KnowledgeAgent | Document Intelligence → Ollama | Placeholder |
| `DOCUMENT_UPLOAD` | PlannerAgent | Placeholder | Planned |
| `IMAGE_ANALYSIS` | PlannerAgent | Placeholder | Planned |
| `MEETING` | MeetingAgent | Placeholder | Planned |
| `TASK_ASSISTANT` | TaskAgent | Placeholder | Planned |
| `FINANCE` | FinanceAgent | Placeholder | Planned |
| `RECOMMENDATION` | RecommendationAgent | Placeholder | Planned |

### Document Intelligence Pipeline

The Document Intelligence Pipeline implements the full document intelligence pipeline. Each stage is an independent class with a clean interface:

```
PDF → OCR (if scanned) → Text Cleaner → Chunker → Embedding Generator
→ Qdrant Vector Store → Retriever → Reranker → Context Builder
→ Permission Guard → Ollama
```

All interfaces are defined — implementations are added incrementally (Phase 5+).

### Document Metadata & Security

Every document carries `DocumentMetadata` with a `DocumentClassification`:

- `PUBLIC` — Non-sensitive information
- `INTERNAL` — Internal company information
- `CONFIDENTIAL` — Sensitive business data
- `HIGHLY_CONFIDENTIAL` — Restricted information

Classification will integrate with RBAC through `PermissionGuard` in a future phase.

### Specialised Agents

The Agent layer is the new orchestration boundary. Each agent is a self-contained unit with three public methods:

| Method | Purpose |
|---|---|
| `execute(context, category)` | Run the agent's core logic |
| `health_check()` | Return agent readiness |
| `supported_categories()` | Declare which `RequestCategory` values the agent handles |

| Agent | Categories | Behaviour |
|---|---|---|
| **KnowledgeAgent** | `GENERAL_CHAT`, `COMPANY_KNOWLEDGE`, `DOCUMENT_QUERY`, `UNKNOWN` | Delegates to the `ExecutionPipeline` (Gemini) or `DocumentIntelligencePipeline` (Ollama). The only agent with real logic today. |
| **PlannerAgent** | `DOCUMENT_UPLOAD`, `IMAGE_ANALYSIS` | Placeholder — returns "Feature planned for upcoming implementation." |
| **MeetingAgent** | `MEETING` | Placeholder |
| **TaskAgent** | `TASK_ASSISTANT` | Placeholder |
| **FinanceAgent** | `FINANCE` | Placeholder |
| **RecommendationAgent** | `RECOMMENDATION` | Placeholder |
| **NotificationAgent** | — | Placeholder (reserved for push/alert sub-system) |

The `AIOrchestrator` no longer dispatches branches directly. It classifies the request, selects the matching agent via `_select_agent()`, and calls `agent.execute()`. This gives every enterprise domain its own isolation boundary — Finance logic lives in `FinanceAgent`, Meeting logic in `MeetingAgent`, etc. — without coupling to a monolithic pipeline.

### Memory System

The memory layer is split into three tiers, each defined as a `BaseMemory` sub-interface:

| Interface | Scope | Future Backend |
|---|---|---|
| `ShortTermMemory` | TTL-expiring key-value (Redis) | `expire(key, ttl)` |
| `LongTermMemory` | Persistent key-value with semantic search (Qdrant/PostgreSQL) | `search(query, top_k)` |
| `ConversationMemory` | Session-scoped message history | `get_history()`, `add_message()`, `clear_session()` |

The `MemoryManager` facade exposes a unified API:

- **`remember(key, value, ttl_seconds?)`** — Store data in the appropriate tier.
- **`recall(key)`** — Retrieve by key, checking short-term first, then long-term.
- **`forget(key)`** — Clear across all tiers.
- **`summarize(key)`** — Return a summary of stored content.

No storage backend ships yet. The interfaces are ready for Redis, Qdrant, and PostgreSQL adapters in later phases.

### Security & Permissions

`PermissionGuard` in `app/security/permission_guard.py` defines the enterprise security contract:

```python
class PermissionGuard(ABC):
    @abstractmethod
    async def can_access_document(
        self,
        user_context: ExecutionContext,
        document: DocumentMetadata,
    ) -> bool:
        ...
```

This single-method interface is designed to be backed by RBAC rules that inspect:

- **User role** — `admin`, `manager`, `executive`, `viewer`
- **Department** — engineering, finance, hr, legal
- **Project** — project-scoped access
- **Document classification** — `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `HIGHLY_CONFIDENTIAL`

The guard sits between the Context Builder and Ollama in the Document Intelligence pipeline, ensuring no document reaches the LLM without authorisation.

### Context Reranker

`BaseReranker` in `app/document_intelligence/reranker/base.py` defines the reranking contract:

```python
class BaseReranker(ABC):
    @abstractmethod
    async def rerank(query, results, top_k) -> list[RetrieverResult]: ...
    @abstractmethod
    async def score(query, document) -> float: ...
```

The reranker improves retrieval quality by scoring and reordering results after the initial vector search. Future implementations can plug in:

- **Cross-Encoder** (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`)
- **BGE Reranker** (e.g. `BAAI/bge-reranker-v2-m3`)

The reranker sits between the Retriever and Context Builder in the Document Intelligence pipeline, inserted as the final step before prompt assembly.

### Why This Completes the Enterprise Architecture

The architecture is now fully layered for enterprise multi-agent execution:

1. **Routes → Services** — Thin validation and business logic (unchanged).
2. **Services → ChatAgent** — Entry point wraps input into `ExecutionContext` (unchanged).
3. **ChatAgent → AI Orchestrator** — Classifies the request (unchanged).
4. **AI Orchestrator → Specialised Agent** — **New.** Orchestrator selects the domain-specific agent via `_select_agent()`.
5. **Specialised Agent → Pipeline** — Agent executes the correct sub-pipeline (KnowledgeAgent today, others tomorrow).
6. **Pipeline → LLM** — Final dispatch to Gemini or Ollama (unchanged).

Every enterprise domain (knowledge, meetings, tasks, finance, recommendations) has its own agent — a bounded context with zero coupling between domains. The Memory system, Permission Guard, and Reranker are defined as pure interfaces, ready for implementation without further architecture changes.

The next development phases are purely implementation:

1. PDF Parsing
2. OCR
3. Chunking
4. Embeddings
5. Qdrant
6. Retrieval
7. Reranking
8. Context Builder
9. Ollama RAG
10. Backend Tool Calling

## API Reference

### `GET /api/v1/health`

Returns service health status.

### `POST /api/v1/chat`

Send a chat message.

```json
{
  "message": "Hello"
}
```

```json
{
  "response": "Hello from Nurofin Executive AI Engine"
}
```

## Environment Variables

The application is configured exclusively through environment variables loaded from `.env`.

```bash
cp .env.example .env
```

Edit `.env` and paste your Gemini API key:

```
GEMINI_API_KEY=your-actual-key-here
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_NAME` | No | `Nurofin Executive AI Engine` | Application name |
| `APP_ENV` | No | `development` | Runtime environment (`development`, `staging`, `production`) |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `GEMINI_API_KEY` | **Yes** | `` | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model identifier |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama3` | Default Ollama model |

> **Security:** `.env` contains secrets and is gitignored. Never commit it. Use `.env.example` as the template for new environments.

## Ollama Setup

The engine supports Ollama as a secondary LLM provider alongside Gemini.

### Install Ollama

```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com/download
```

### Pull a model

```bash
ollama pull llama3
```

Ollama supports many models — swap `llama3` for `mistral`, `phi`, `qwen2`, etc. by changing `OLLAMA_MODEL` in `.env`.

### Start Ollama

```bash
ollama serve
```

By default Ollama listens on `http://localhost:11434`. Configure via `OLLAMA_BASE_URL` in `.env`.

### Verify

```bash
curl http://localhost:11434/api/tags
```

### Provider Health

```
GET /api/v1/health/models
```

Returns the status of both providers without crashing if one is down.

```json
{
  "gemini": "healthy",
  "ollama": "unreachable"
}
```
