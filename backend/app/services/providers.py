"""External-provider adapters. Every provider is optional but never silently simulated."""

import hashlib
import json
from typing import Any

import httpx

from app.config import settings


def provider_status() -> dict[str, bool]:
    config = settings()
    return {
        "fireworks": bool(config.fireworks_api_key and config.fireworks_model),
        "upstash_redis": bool(config.upstash_redis_rest_url and config.upstash_redis_rest_token),
        "qdrant": bool(
            config.qdrant_url and config.qdrant_api_key and config.fireworks_embedding_model
        ),
        "tavily": bool(config.tavily_api_key),
    }


def cache_key(namespace: str, value: str) -> str:
    return f"atlas:{namespace}:{hashlib.sha256(value.encode()).hexdigest()}"


def redis_get(key: str) -> Any | None:
    config = settings()
    if not provider_status()["upstash_redis"]:
        return None
    response = httpx.post(
        config.upstash_redis_rest_url,
        headers={"Authorization": f"Bearer {config.upstash_redis_rest_token}"},
        json=["GET", key],
        timeout=5,
    )
    response.raise_for_status()
    value = response.json().get("result")
    return json.loads(value) if value else None


def redis_set(key: str, value: Any) -> None:
    config = settings()
    if not provider_status()["upstash_redis"]:
        return
    response = httpx.post(
        config.upstash_redis_rest_url,
        headers={"Authorization": f"Bearer {config.upstash_redis_rest_token}"},
        json=["SET", key, json.dumps(value), "EX", config.research_cache_ttl_seconds],
        timeout=5,
    )
    response.raise_for_status()


def fireworks_chat(system: str, user: str) -> str | None:
    config = settings()
    if not provider_status()["fireworks"]:
        return None
    response = httpx.post(
        f"{config.fireworks_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {config.fireworks_api_key}"},
        json={
            "model": config.fireworks_model,
            "temperature": 0.1,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def tavily_search(query: str) -> list[dict[str, Any]]:
    """Fetch current web evidence and normalize it for Atlas source persistence."""
    config = settings()
    if not provider_status()["tavily"]:
        return []
    response = httpx.post(
        config.tavily_url,
        json={
            "api_key": config.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 5,
            "include_raw_content": "text",
        },
        timeout=20,
    )
    response.raise_for_status()
    return [
        {
            "title": item.get("title", "Untitled web source"),
            "url": item.get("url", ""),
            "content": item.get("raw_content") or item.get("content") or "",
            "score": float(item.get("score", 0.5)),
        }
        for item in response.json().get("results", [])
    ]


def fireworks_embedding(text: str) -> list[float] | None:
    config = settings()
    if not config.fireworks_api_key or not config.fireworks_embedding_model:
        return None
    response = httpx.post(
        f"{config.fireworks_base_url.rstrip('/')}/embeddings",
        headers={"Authorization": f"Bearer {config.fireworks_api_key}"},
        json={"model": config.fireworks_embedding_model, "input": text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def qdrant_upsert(point_id: str, text: str, payload: dict[str, Any]) -> bool:
    config = settings()
    vector = fireworks_embedding(text)
    if not vector or not provider_status()["qdrant"]:
        return False
    headers = {"api-key": config.qdrant_api_key}
    base = config.qdrant_url.rstrip("/")
    httpx.put(
        f"{base}/collections/{config.qdrant_collection}",
        headers=headers,
        json={"vectors": {"size": len(vector), "distance": "Cosine"}},
        timeout=10,
    )
    response = httpx.put(
        f"{base}/collections/{config.qdrant_collection}/points?wait=true",
        headers=headers,
        json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        timeout=15,
    )
    response.raise_for_status()
    return True
