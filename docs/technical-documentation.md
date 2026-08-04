# Technical Documentation & System Design

## System Overview

Enterprise Research Agent (Atlas) is designed for enterprise intelligence teams and researchers who require reliable, evidence-backed answers to complex inquiries. Unlike standard conversational AI wrappers, Atlas enforces strict evidence provenance, claim extraction, stance cross-verification, and multi-LLM failovers.

---

## Core Technical Principles

1. **Evidence-First Provenance**: Every synthesized statement must map directly to an extracted finding (`Finding`) tied to a verified source (`Source` or `Document`).
2. **Auditability & Traceability**: Pipeline execution is recorded as granular `RunEvent` steps, while external LLM calls log token counts, latency, and estimated USD costs in `LlmCall`.
3. **Multi-Stage Graph Execution**: Workflow steps are managed by a 7-stage deterministic LangGraph state machine rather than an unstructured agent loop.
4. **Resilient Provider Fallback**: Automatic multi-tier failovers ensure system availability even during external API rate limits or outages.

---

## LangGraph 7-Stage Execution Pipeline

The research pipeline is implemented as a compiled `StateGraph` in `backend/app/services/research.py`:

```text
START ──► [plan] ──► [retrieve] ──► [store] ──► [extract] ──► [entities] ──► [compare] ──► [synthesize] ──► END
```

| Node Name | Function | Input / State | Output / Effect |
|---|---|---|---|
| `plan` | Decomposes user question into targeted sub-queries | `question` | `sub_queries: list[str]` |
| `retrieve` | Queries OpenAlex, Tavily Search, and local PDF/TXT docs | `sub_queries` | `raw_sources: list[dict]` |
| `store` | Saves sources to database, generates chunks, upserts Qdrant vectors | `raw_sources` | `stored_source_ids: list[str]` |
| `extract` | Extracts factual claims, evidence spans, and initial confidence | `stored_source_ids` | `finding_ids: list[str]` |
| `entities` | Recognizes named entities, canonical keys, and mentions | `finding_ids` | `entity_ids: list[str]` |
| `compare` | Cross-checks claims for contradictions and stance alignment | `finding_ids` | `contradiction_count: int` |
| `synthesize` | Generates structured executive briefing via Fireworks/Groq LLM | `findings`, `contradictions` | `conclusion`, `confidence`, status: `completed` |

---

## Scoring & Stance Analysis Algorithms

### 1. Finding Confidence Calculation
Each extracted claim receives an initial confidence score based on source type and publisher reliability:
- **Academic / Peer-reviewed (OpenAlex)**: Base reliability $0.85 - 0.95$
- **Verified Web Articles (Tavily)**: Base reliability $0.70 - 0.85$
- **User Document Uploads**: Base reliability $0.80$

### 2. Contradiction Penalty & Session Confidence Formula
During the `compare` phase, pair-wise findings share topic keys and undergo stance comparison (`supports`, `contradicts`, `neutral`).

If two findings contradict each other:
1. The stance for both findings is updated to `contradicted`.
2. A record is created in `ClaimComparison`.
3. The overall session confidence score is adjusted according to the formula:

$$\text{Session Confidence} = \max\left(0.0,\, \frac{1}{N}\sum_{i=1}^N c_i - (K_{\text{contradictions}} \times 0.04)\right)$$

Where:
- $N$ is the total number of top findings evaluated ($N \le 8$).
- $c_i$ is the confidence score of finding $i$.
- $K_{\text{contradictions}}$ is the total number of detected contradiction pairs.

---

## Hybrid Search & Semantic Caching Strategy

```text
                   User Search Query
                          │
                          ▼
           ┌─────────────────────────────┐
           │ Vector Embedding Generation │
           │(fireworks/qwen3-embedding)  │
           └──────────────┬──────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
  ┌───────────────────┐       ┌───────────────────┐
  │ Qdrant Vector Search│     │  SQL Text Fallback│
  │ (Cosine Similarity)│      │  (LIKE Pattern)   │
  └─────────┬─────────┘       └─────────┬─────────┘
            │                           │
            └─────────────┬─────────────┘
                          │
                          ▼
             Merged Knowledge Results
```

1. **Dense Vector Search**: Embeds user query using Fireworks Qwen3-Embedding (`8192` dimension) and executes cosine similarity search in Qdrant collection `atlas_evidence`.
2. **SQL Fallback**: If Qdrant is unreachable or unconfigured, Atlas executes indexed full-text `LIKE` searches across `Source` abstracts and `Finding` claims.
3. **Redis Semantic Caching**: Caches raw JSON responses for frequent queries with configurable TTL (`RESEARCH_CACHE_TTL_SECONDS=3600`).

---

## Multi-Provider LLM Fallback Mechanism

Atlas includes a provider manager (`backend/app/services/providers.py`) that handles LLM selection, retry logic, and latency profiling:

```text
Attempt 1: Fireworks AI (DeepSeek-v3 / DeepSeek-r1)
   │
   ├─► Success ──► Log token usage & latency ──► Return result
   │
   └─► HTTP Error / Timeout / 5xx
         │
         ▼
Attempt 2: Groq API (Llama-3.3-70b-versatile)
   │
   ├─► Success ──► Log token usage & fallback rate ──► Return result
   │
   └─► HTTP Error / Timeout / 5xx
         │
         ▼
Attempt 3: Deterministic Local Fallback Engine
   │
   └─► Formats top evidence claims into deterministic text response
```

---

## Telemetry & Operational Metrics

Operational statistics are tracked in real-time via `GET /v1/metrics/overview`:
- **Total Research Sessions & Completed Runs**
- **Average System Confidence**
- **LLM Call Volume & Provider Breakdown** (Fireworks vs. Groq)
- **Token Consumption & Estimated Cost (USD)**
- **Latency Percentiles**: Latency distributions ($p50$, $p95$) calculated over logged `LlmCall` durations.
