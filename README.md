# Enterprise Research Agent (Atlas)

## Overview

Enterprise Research Agent (Atlas) is an evidence-first, autonomous research orchestration system designed to retrieve, analyze, index, synthesize, and verify enterprise and scientific intelligence. Powered by a 7-stage LangGraph execution pipeline, multi-provider LLM synthesis, hybrid vector search with Qdrant, Redis semantic caching, and full evidence-claim tracking with contradiction detection.

The system is designed to be:
- **Evidence-First & Audit-Ready**
- **Multi-Source Retrieval** (OpenAlex scholarly database, Tavily live web search, local PDF/TXT documents)
- **Multi-Provider LLM Integration** (Fireworks AI, Groq, and deterministic fallbacks)
- **Durable Vector Indexing & Semantic Caching** (Qdrant & Redis)
- **Fast & Resilient with Graceful Degradation**


## Key Features

- **7-Stage LangGraph Research Workflow** (`plan` → `retrieve` → `store` → `extract` → `entities` → `compare` → `synthesize`)
- **Scholarly & Live Web Search Integration** via OpenAlex API and Tavily Search
- **Durable Document Ingestion** supporting local `.pdf` and `.txt` evidence upload
- **Vector Indexing & Hybrid Search** using Qdrant vector database
- **Semantic Caching & Deduplication** powered by Redis
- **Multi-LLM Orchestration** supporting Fireworks AI (`DeepSeek-v3/r1`) and Groq (`Llama-3.3-70b`)
- **Entity Extraction & Stance Analysis** for cross-verifying findings and identifying contradictions
- **Executive Report Generation** with downloadable executive briefs and audit trace logs
- **Real-time Pipeline Telemetry & Metrics** tracking session performance, cache hits, and latency
- **Modern Interactive Dashboard** built with Next.js 16, Tailwind CSS, and Lucide icons


## Technology Stack

- **Python 3.12**
- **FastAPI & Uvicorn**
- **LangGraph** (StateGraph pipeline orchestration)
- **SQLAlchemy & SQLite / PostgreSQL**
- **Redis** (Semantic caching)
- **Qdrant** (Vector similarity engine)
- **Fireworks AI & Groq** (LLM providers)
- **httpx & PyPDF**
- **Next.js 16** (App Router & Turbopack)
- **TypeScript & React**
- **Tailwind CSS & Lucide React**
- **Ruff & Pytest**


## Setup

```bash
# Clone the repository
git clone https://github.com/adityakanamadi281/Enterprise-Research-Agent.git

# Navigate to the project directory
cd Enterprise-Research-Agent
```

### Option A: Docker Compose (Quickstart)

```bash
# Setup environment variables
cp .env.example .env

# Build and launch all services (Backend, Frontend, Redis)
docker compose up --build
```

### Option B: Manual Local Setup

#### 1. Backend Setup

```bash
cd backend

# Create environment configuration file
cp .env.example .env

# Install dependencies using uv
uv sync --all-groups

# Start the FastAPI server in reload mode
uv run uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup

```bash
cd frontend

# Create local environment configuration file
cp .env.local.example .env.local

# Install Node.js dependencies
npm install

# Start the Next.js development server
npm run dev
```


## Run

Access the running applications:

- **Frontend Dashboard:** `http://localhost:3000`
- **Backend API Docs (Swagger):** `http://localhost:8000/docs`
- **Health Check Endpoint:** `http://localhost:8000/v1/health`


## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./atlas.db` | Database connection string (SQLite locally; PostgreSQL in production) |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed origin domains for CORS |
| `ATLAS_API_KEY` | *(unset)* | API key required in header `X-API-Key` if specified |
| `FIREWORKS_API_KEY` | *(unset)* | Fireworks AI key for LLM research planning & synthesis |
| `FIREWORKS_MODEL` | `accounts/fireworks/models/deepseek-v3p1` | Target Fireworks model |
| `FIREWORKS_EMBEDDING_MODEL` | `fireworks/qwen3-embedding-8b` | Target embedding model |
| `GROQ_API_KEY` | *(unset)* | Groq API key for alternative LLM provider |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Target Groq model |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL for semantic caching |
| `TAVILY_API_KEY` | *(unset)* | Tavily Search API key for real-time web research |
| `QDRANT_URL` | *(unset)* | Qdrant Vector database instance URL |
| `QDRANT_API_KEY` | *(unset)* | Qdrant API authorization key |
| `QDRANT_COLLECTION` | `atlas_evidence` | Qdrant collection name for vector indexing |


## Project Structure

```text
Enterprise-Research-Agent/
├── .env.example                 # Global environment configuration guide
├── Dockerfile                   # Workspace Docker container build definition
├── docker-compose.yml           # Multi-container orchestration (Backend, Frontend, Redis)
├── README.md                    # Project documentation
├── backend/
│   ├── app/
│   │   ├── api/                 # REST API endpoints & authorization middleware
│   │   │   ├── routes.py
│   │   │   └── security.py
│   │   ├── domain/              # SQLAlchemy database models & Pydantic schemas
│   │   │   └── models.py
│   │   ├── services/            # Core business logic & provider integrations
│   │   │   ├── audit.py         # Metrics & operational telemetry aggregation
│   │   │   ├── documents.py     # PDF & TXT document parsing & text extraction
│   │   │   ├── providers.py     # External LLM, search, & vector store clients
│   │   │   └── research.py      # LangGraph state machine & orchestration
│   │   ├── config.py            # Environment settings & configuration validation
│   │   └── main.py              # FastAPI application initialization
│   ├── scripts/
│   │   └── evaluate.py          # Benchmark evaluation script
│   ├── tests/                   # Pytest test suite
│   │   ├── test_api.py
│   │   ├── test_knowledge.py
│   │   └── test_research.py
│   ├── Dockerfile               # Backend container definition
│   └── pyproject.toml           # Python metadata & uv package dependencies
└── frontend/
    ├── app/                     # Next.js App Router layout and pages
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── styles.css
    ├── components/              # Reusable React components
    │   ├── CitationsPanel.tsx   # Dynamic evidence & citation inspector
    │   ├── MainFeed.tsx         # Central workspace feed & search timeline
    │   ├── ReportModal.tsx      # Executive report generator & viewer
    │   └── Sidebar.tsx          # Session history & drawer navigation
    ├── Dockerfile               # Frontend container definition
    ├── package.json             # Frontend npm dependencies and scripts
    ├── tailwind.config.js       # Tailwind CSS configuration
    └── tsconfig.json            # TypeScript compiler configuration
```


## Research Pipeline & Scoring

```text
    [ START ]
        │
        ▼
   ┌─────────┐     Generates strategic search queries
   │  Plan   │ ──► based on user research prompt
   └────┬────┘
        │
        ▼
   ┌─────────┐     Queries OpenAlex, Tavily Web,
   │Retrieve │ ──► and uploaded local documents
   └────┬────┘
        │
        ▼
   ┌─────────┐     Persists evidence sources and
   │  Store  │ ──► indexes vectors in Qdrant & Redis
   └────┬────┘
        │
        ▼
   ┌─────────┐     Extracts granular claim statements
   │ Extract │ ──► and calculates initial confidence
   └────┬────┘
        │
        ▼
   ┌─────────┐     Identifies key entities, organizations,
   │Entities │ ──► and domain topics across evidence
   └────┬────┘
        │
        ▼
   ┌─────────┐     Cross-checks claims for contradictions
   │ Compare │ ──► and penalizes confidence if conflict exists
   └────┬────┘
        │
        ▼
   ┌─────────┐     Synthesizes executive briefing using
   │Synthesize──► Fireworks AI / Groq LLMs
   └────┬────┘
        │
        ▼
    [  END  ]
```

### Confidence Scoring Calculation

The overall research confidence score is calculated based on mean findings confidence penalised by detected evidence contradictions:

$$\text{Confidence} = \max\left(0,\, \frac{1}{N}\sum_{i=1}^N \text{ClaimConfidence}_i - (\text{Contradictions} \times 0.04)\right)$$


## Tests

Execute the static analysis tools and unit tests in the `backend` directory:

```bash
cd backend

# Run code style and lint checks with Ruff
uv run ruff check app tests scripts

# Execute unit and integration tests
uv run pytest

# Run golden-set evaluation benchmark
uv run python scripts/evaluate.py
```


## Docker

Launch all application services using Docker Compose:

```bash
docker build -t enterprise-research-backend ./backend
docker build -t enterprise-research-frontend ./frontend

# Or launch all services together
docker compose up --build
```
