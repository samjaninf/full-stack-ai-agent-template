# {{ cookiecutter.project_name }}

{{ cookiecutter.project_description }}

Generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template).

## Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI + Pydantic v2 |
{%- if cookiecutter.use_postgresql %}
| **Database** | PostgreSQL (async) |
{%- elif cookiecutter.use_mongodb %}
| **Database** | MongoDB (async) |
{%- elif cookiecutter.use_sqlite %}
| **Database** | SQLite |
{%- endif %}
| **Auth** | JWT + API Key + refresh tokens |
{%- if cookiecutter.enable_redis %}
| **Cache** | Redis |
{%- endif %}
| **AI Framework** | {{ cookiecutter.ai_framework }} ({{ cookiecutter.llm_provider }}) |
{%- if cookiecutter.enable_rag %}
| **RAG** | {{ cookiecutter.vector_store }} vector store |
{%- endif %}
{%- if cookiecutter.background_tasks != "none" %}
| **Tasks** | {{ cookiecutter.background_tasks }} |
{%- endif %}
{%- if cookiecutter.use_frontend %}
| **Frontend** | Next.js 15 + React 19 + Tailwind v4 |
{%- endif %}

## Quick Start

```bash
# Install dependencies
make install

{%- if cookiecutter.enable_docker %}
# One-command setup (Docker required)
make quickstart
{%- else %}
# Start the server
make run
{%- endif %}
```

{%- if cookiecutter.enable_docker %}
This will:
1. Install Python dependencies
2. Start all Docker services (database, Redis, vector store, etc.)
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
3. Run database migrations
{%- endif %}
4. Create an admin user (`admin@example.com` / `admin123`)
{%- endif %}

**Access:**
- API: http://localhost:{{ cookiecutter.backend_port }}
- Docs: http://localhost:{{ cookiecutter.backend_port }}/docs
- Admin: http://localhost:{{ cookiecutter.backend_port }}/admin
{%- if cookiecutter.use_frontend %}
- Frontend: http://localhost:{{ cookiecutter.frontend_port }} (run `cd frontend && bun dev`)
{%- endif %}

## Manual Setup

If you prefer to set up step by step:

```bash
# 1. Install dependencies
make install

{%- if cookiecutter.use_postgresql and cookiecutter.enable_docker %}
# 2. Start database
make docker-db
{%- endif %}

{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
# 3. Create and apply migrations
make db-migrate    # Enter: "Initial migration"
make db-upgrade
{%- endif %}

# 4. Create admin user
make create-admin

# 5. Start backend
make run

{%- if cookiecutter.use_frontend %}
# 6. Start frontend (new terminal)
cd frontend && bun install && bun dev
{%- endif %}
```

## Commands

Run `make help` for all available commands. Key ones:

| Command | Description |
|---------|-------------|
| `make run` | Start dev server with hot reload |
| `make test` | Run tests |
| `make lint` | Check code quality |
| `make format` | Auto-format code |
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
| `make db-migrate` | Create new migration |
| `make db-upgrade` | Apply migrations |
{%- endif %}
| `make create-admin` | Create admin user |
{%- if cookiecutter.enable_docker %}
| `make quickstart` | Full setup (install + docker + db + admin) |
| `make docker-up` | Start all Docker services |
| `make docker-down` | Stop all services |
{%- endif %}


## AI Agent

Using **{{ cookiecutter.ai_framework }}** with **{{ cookiecutter.llm_provider }}** provider.

{%- if cookiecutter.use_frontend %}
Chat with the agent at http://localhost:{{ cookiecutter.frontend_port }}/chat
{%- endif %}

### Customize

- **System prompt:** `app/agents/prompts.py`
- **Add tools:** See `docs/howto/add-agent-tool.md`
- **Agent config:** `.env` → `AI_MODEL`, `AI_TEMPERATURE`

## Message Ratings

Users can rate AI responses with 👍/👎 and optional feedback comments.
Administrators can view analytics and export rating data.

{%- if cookiecutter.use_frontend %}
- Rate messages at http://localhost:{{ cookiecutter.frontend_port }}/chat
- Admin dashboard at http://localhost:{{ cookiecutter.frontend_port }}/admin/ratings
{%- endif %}

See `docs/howto/use-ratings.md` for full documentation.

{%- if cookiecutter.enable_rag %}

## RAG (Knowledge Base)

Using **{{ cookiecutter.vector_store }}** as vector store.

### Ingest documents

```bash
# Local files
uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/docs/ --collection documents --recursive

{%- if cookiecutter.enable_google_drive_ingestion %}
# Google Drive
uv run {{ cookiecutter.project_slug }} rag-sync-gdrive --collection documents --folder-id <id>
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
# S3/MinIO
uv run {{ cookiecutter.project_slug }} rag-sync-s3 --collection documents --prefix docs/
{%- endif %}
```

### Search

```bash
uv run {{ cookiecutter.project_slug }} rag-search "your query" --collection documents
```

### Manage collections

```bash
uv run {{ cookiecutter.project_slug }} rag-collections   # List all
uv run {{ cookiecutter.project_slug }} rag-stats          # Show stats
uv run {{ cookiecutter.project_slug }} rag-drop <name>    # Delete collection
```

### Sync sources

Sync sources let you configure recurring document ingestion from external
systems (Google Drive, S3, etc.) via the API or CLI.

```bash
uv run {{ cookiecutter.project_slug }} cmd rag-sources          # List configured sources
uv run {{ cookiecutter.project_slug }} cmd rag-source-add       # Add a new source
uv run {{ cookiecutter.project_slug }} cmd rag-source-sync      # Trigger sync for a source
uv run {{ cookiecutter.project_slug }} cmd rag-source-remove    # Remove a source
```

See `docs/howto/add-sync-connector.md` for how to add custom connectors.
{%- endif %}

## Project Structure

```
backend/app/
├── api/routes/v1/        # API endpoints
├── core/config.py        # Settings (from .env)
├── services/             # Business logic
├── repositories/         # Data access
├── schemas/              # Pydantic models
{%- if cookiecutter.use_database %}
├── db/models/            # Database models
{%- endif %}
├── agents/               # AI agents & tools
{%- if cookiecutter.enable_rag %}
├── rag/                  # RAG pipeline (embeddings, vector store, ingestion)
│   └── connectors/       # Sync source connectors
{%- endif %}
├── commands/             # CLI commands (auto-discovered)
{%- if cookiecutter.background_tasks != "none" %}
└── worker/               # Background tasks
{%- else %}
└── ...
{%- endif %}
```

## Guides

| Guide | Description |
|-------|-------------|
| `docs/howto/add-api-endpoint.md` | Add a new API endpoint |
| `docs/howto/add-agent-tool.md` | Create a new agent tool |
| `docs/howto/customize-agent-prompt.md` | Customize agent behavior |
| `docs/howto/add-background-task.md` | Add background tasks |
{%- if cookiecutter.enable_rag %}
| `docs/howto/add-rag-source.md` | Add a new RAG document source |
| `docs/howto/add-sync-connector.md` | Create a new sync connector |
{%- endif %}

## Environment Variables

All config is in `backend/.env`. Key variables:

```bash
{%- if cookiecutter.use_postgresql %}
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=postgres
{%- endif %}
{%- if cookiecutter.use_openai %}
OPENAI_API_KEY=sk-...
{%- endif %}
{%- if cookiecutter.use_anthropic %}
ANTHROPIC_API_KEY=sk-ant-...
{%- endif %}
{%- if cookiecutter.use_google %}
GOOGLE_API_KEY=...
{%- endif %}
{%- if cookiecutter.enable_rag %}
RAG_CHUNKING_STRATEGY=recursive  # recursive, markdown, fixed
RAG_HYBRID_SEARCH=false
{%- endif %}
```

See `backend/.env.example` for all available variables.

{%- if cookiecutter.use_frontend %}

## Deployment

### Frontend (Vercel)

```bash
cd frontend
npx vercel --prod
```

Set environment variables in Vercel dashboard:
- `BACKEND_URL` = your backend URL
- `BACKEND_WS_URL` = your backend WebSocket URL
- `NEXT_PUBLIC_AUTH_ENABLED` = `true`
{%- if cookiecutter.enable_rag %}
- `NEXT_PUBLIC_RAG_ENABLED` = `true`
{%- endif %}

### Backend (Docker)

```bash
make docker-prod
```
{%- endif %}

---

*Generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template) v{{ cookiecutter.generator_version }}*
