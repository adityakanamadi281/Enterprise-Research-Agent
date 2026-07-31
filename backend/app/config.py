import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, field_validator


def load_dotenv(path: Path) -> None:
    """Load development variables without adding a runtime dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(Path(__file__).parents[2] / ".env")


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./atlas.db")
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    research_provider: str = os.getenv("RESEARCH_PROVIDER", "openalex")
    openalex_url: str = os.getenv("OPENALEX_URL", "https://api.openalex.org/works")
    openalex_api_key: str | None = os.getenv("OPENALEX_API_KEY")
    fireworks_api_key: str | None = os.getenv("FIREWORKS_API_KEY")
    fireworks_base_url: str = os.getenv(
        "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
    )
    fireworks_model: str | None = os.getenv("FIREWORKS_MODEL")
    fireworks_embedding_model: str | None = os.getenv("FIREWORKS_EMBEDDING_MODEL")
    upstash_redis_rest_url: str | None = os.getenv("UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: str | None = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    research_cache_ttl_seconds: int = int(os.getenv("RESEARCH_CACHE_TTL_SECONDS", "3600"))
    qdrant_url: str | None = os.getenv("QDRANT_URL")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "atlas_evidence")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    tavily_url: str = os.getenv("TAVILY_URL", "https://api.tavily.com/search")
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    api_key: str | None = os.getenv("ATLAS_API_KEY")
    environment: str = os.getenv("ENVIRONMENT", "development")

    @field_validator("research_provider")
    @classmethod
    def supported_provider(cls, value: str) -> str:
        if value.lower() != "openalex":
            raise ValueError(
                "RESEARCH_PROVIDER must be openalex until another provider adapter is enabled"
            )
        return value.lower()


@lru_cache
def settings() -> Settings:
    return Settings()
