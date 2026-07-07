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
├── api/          HTTP endpoints (thin handlers)
├── agents/       AI agent implementations
├── core/         Config, logging, exceptions, DI
├── memory/       Chat memory backends
├── models/       AI model integrations (Gemini, Ollama)
├── prompts/      Prompt templates
├── rag/          Retrieval-Augmented Generation
├── router/       Orchestration layer
├── schemas/      Pydantic request/response models
├── services/     Business logic
├── storage/      Storage backends
├── tools/        Tool/function calling
└── main.py       Application entry point
```

## Architecture

```
API Layer  →  Router  →  Services  →  Agents  →  Models
```

Each layer has a single responsibility. Routes validate and delegate. Services contain business logic. Agents encapsulate AI behaviour. Models wrap LLM providers.

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
