# API Reference & Swagger Specifications

## Overview

The Enterprise Research Agent (Atlas) REST API provides endpoints for executing research sessions, retrieving live Server-Sent Events (SSE), uploading documents, generating executive briefs, searching knowledge bases, and inspecting operational telemetry.

**API Swagger Interactive Docs**: [https://enterprise-research-agent-1.onrender.com/docs](https://enterprise-research-agent-1.onrender.com/docs)
> **Base URL**: `http://localhost:8000/v1`  
> **Interactive Swagger Documentation**: `http://localhost:8000/docs`  
> **ReDoc Specifications**: `http://localhost:8000/redoc`

---

## Authentication

If the `ATLAS_API_KEY` environment variable is set on the server, all requests to endpoints under `/v1/*` must include the custom header `X-API-Key`.

```http
X-API-Key: your_atlas_secret_api_key
```

If `ATLAS_API_KEY` is empty or omitted in `.env`, authentication is bypassed for local development.

---

## Endpoint Summary Matrix

| Method | Endpoint Path | Description | Status Code |
|---|---|---|---|
| `GET` | `/v1/health` | Service health status check | `200 OK` |
| `POST` | `/v1/research` | Submit synchronous research task | `201 Created` |
| `POST` | `/v1/research/async` | Submit background research task | `202 Accepted` |
| `GET` | `/v1/research/{id}/events/stream` | Stream real-time execution events (SSE) | `200 OK` |
| `GET` | `/v1/research` | List past 50 research sessions | `200 OK` |
| `GET` | `/v1/research/{id}` | Retrieve complete research session details | `200 OK` |
| `POST` | `/v1/documents/upload` | Upload `.pdf` or `.txt` evidence files | `201 Created` |
| `POST` | `/v1/research/{id}/report` | Generate formatted executive brief report | `200 OK` |
| `GET` | `/v1/research/{id}/report` | Fetch generated executive report | `200 OK` |
| `POST` | `/v1/organizations` | Create tenant organization | `201 Created` |
| `POST` | `/v1/projects` | Create research project | `201 Created` |
| `GET` | `/v1/projects` | List all research projects | `200 OK` |
| `GET` | `/v1/metrics/overview` | Fetch operational telemetry & cost metrics | `200 OK` |
| `GET` | `/v1/knowledge/search` | Execute hybrid vector/SQL knowledge search | `200 OK` |

---

## Endpoint Details & Examples

### 1. Health Check
`GET /v1/health`

#### Response (`200 OK`):
```json
{
  "status": "ok",
  "service": "atlas-api"
}
```

---

### 2. Submit Synchronous Research Task
`POST /v1/research`

Executes the full 7-stage LangGraph research workflow synchronously and returns the complete synthesized session.

#### Request Body (`application/json`):
```json
{
  "question": "What are recent developments in quantum error correction and fault tolerant surface codes?",
  "project_id": null
}
```

#### Response (`201 Created`):
```json
{
  "id": "e9b421a8-8f12-4c22-901a-6d0d2a2a0112",
  "question": "What are recent developments in quantum error correction and fault tolerant surface codes?",
  "status": "completed",
  "confidence": 0.88,
  "conclusion": "### Overview & Explanation\nQuantum error correction has seen significant advances...",
  "created_at": "2026-08-04T10:00:00Z",
  "completed_at": "2026-08-04T10:00:05Z",
  "sources": [
    {
      "id": "src-101",
      "title": "Fault-Tolerant Quantum Computation with Surface Codes",
      "url": "https://api.openalex.org/works/W212345678",
      "publisher": "OpenAlex",
      "reliability_score": 0.9
    }
  ],
  "findings": [
    {
      "id": "fnd-201",
      "claim": "Surface codes achieve error threshold near 1% under circuit-level noise models.",
      "confidence": 0.9,
      "stance": "supports"
    }
  ],
  "entities": [
    {
      "name": "Surface Codes",
      "entity_type": "concept",
      "confidence": 0.85
    }
  ]
}
```

---

### 3. Submit Background Research Task (Async)
`POST /v1/research/async`

Queues a research task for execution in background worker threads. Returns immediately with `202 Accepted` and a `queued` status.

#### Response (`202 Accepted`):
```json
{
  "id": "e9b421a8-8f12-4c22-901a-6d0d2a2a0112",
  "question": "What are recent developments in quantum error correction?",
  "status": "queued",
  "confidence": 0.0,
  "created_at": "2026-08-04T10:00:00Z"
}
```

---

### 4. Stream Pipeline Events (Server-Sent Events)
`GET /v1/research/{id}/events/stream`

Establishes a continuous SSE event stream streaming live step progress updates as nodes execute in the LangGraph pipeline.

#### Stream Chunk Format (`text/event-stream`):
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

data: {"status": "running", "events": [{"step": "plan", "status": "completed", "details": {"sub_queries": 3}, "created_at": "2026-08-04T10:00:01Z"}]}

data: {"status": "running", "events": [{"step": "plan", "status": "completed"}, {"step": "retrieve", "status": "completed", "details": {"sources_count": 8}}]}

data: {"status": "completed", "events": [...]}
```

---

### 5. Document Upload
`POST /v1/documents/upload`

Parses uploaded physical `.pdf` or `.txt` evidence files, stores plain-text content, creates evidence findings, and upserts dense vector embeddings into Qdrant.

#### Form Request (`multipart/form-data`):
- `files`: File upload binary (`.pdf` or `.txt`)
- `research_session_id` (Optional): ID of target research session to attach document.

#### Response (`201 Created`):
```json
{
  "documents": [
    {
      "document_id": "doc-5501",
      "session_id": "e9b421a8-8f12-4c22-901a-6d0d2a2a0112",
      "filename": "quantum_benchmark_report.pdf",
      "characters": 18420,
      "vector_indexed": true
    }
  ]
}
```

---

### 6. Generate Executive Report
`POST /v1/research/{id}/report`

Generates an executive report containing session findings, entity linkages, audit trails, and citations.

#### Request Body (`application/json`):
```json
{
  "title": "Executive Briefing: Quantum Error Correction Horizon"
}
```

#### Response (`200 OK`):
```json
{
  "id": "rep-901",
  "research_session_id": "e9b421a8-8f12-4c22-901a-6d0d2a2a0112",
  "title": "Executive Briefing: Quantum Error Correction Horizon",
  "generated_at": "2026-08-04T10:01:00Z",
  "content": {
    "question": "What are recent developments in quantum error correction?",
    "confidence": 0.88,
    "conclusion": "### Overview & Explanation...",
    "sources_count": 8,
    "findings_count": 12,
    "entities_count": 6
  }
}
```

---

### 7. Telemetry & Operations Dashboard Metrics
`GET /v1/metrics/overview`

Returns system usage statistics, LLM call volumes, provider breakdowns, token usage, latency distribution, and estimated cost tracking.

#### Response (`200 OK`):
```json
{
  "sessions": 42,
  "sources": 310,
  "findings": 850,
  "events": 294,
  "completed_runs": 40,
  "average_confidence": 0.84,
  "measured_at": "2026-08-04T10:02:00Z",
  "llm": {
    "total_calls": 84,
    "total_tokens": 142500,
    "total_estimated_cost_usd": 0.0425,
    "provider_usage": {
      "fireworks": 78,
      "groq": 6
    },
    "fallback_rate": 0.071,
    "p50_latency_ms": 1240.5,
    "p95_latency_ms": 3120.0
  }
}
```

---

### 8. Hybrid Knowledge Search
`GET /v1/knowledge/search?q=quantum`

Executes hybrid vector similarity search via Qdrant (with fallback to SQL full-text search) across indexed research sources and document uploads.

#### Response (`200 OK`):
```json
[
  {
    "id": "src-101",
    "session_id": "e9b421a8-8f12-4c22-901a-6d0d2a2a0112",
    "title": "Fault-Tolerant Quantum Computation with Surface Codes",
    "url": "https://api.openalex.org/works/W212345678",
    "publisher": "OpenAlex",
    "abstract": "Surface codes represent a leading candidate for quantum error correction...",
    "confidence": 0.88,
    "created_at": "2026-08-04T10:00:00Z"
  }
]
```
