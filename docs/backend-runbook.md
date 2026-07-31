# Backend runbook

## Local operation

```bash
cd backend
uv sync --all-groups
uv run uvicorn app.main:app --reload
```

The service starts at `http://localhost:8000`; OpenAPI documentation is served at `/docs`.

## Health checks

- Liveness: `GET /v1/health`
- Operational counts: `GET /v1/metrics/overview`
- Audit history: `GET /v1/audit-logs`

## Security posture

- API-key enforcement is enabled by setting `ATLAS_API_KEY`; local development intentionally remains credential-free.
- CORS is allowlisted through `CORS_ORIGINS`.
- Response headers prevent MIME sniffing, clickjacking, and cross-origin referrer leakage.
- Audit records exclude request bodies and evidence content; they record action type, resource and correlation-ready request ID field.

## Data lifecycle

Research sessions own sources, findings and execution events. Reports are immutable snapshots of a session's retained evidence. The startup routine safely adds the `project_id` field to prior SQLite demo databases. Use an Alembic migration workflow before deploying shared PostgreSQL environments.

## Scale plan

1. Move `run_research` to a durable worker queue and return a run ID immediately.
2. Stream `run_events` with SSE.
3. Add Qdrant hybrid retrieval and a cross-encoder behind the current knowledge-search contract.
4. Enforce organization-scoped queries with PostgreSQL row-level security and OIDC roles.
5. Emit OpenTelemetry spans using the existing research-session ID as the trace correlation key.
