from fastapi import Header, HTTPException, Request, status

from app.config import settings


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    """Secure production deployments without making local demos require credentials."""
    configured_key = settings().api_key
    if configured_key and x_api_key != configured_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")
    request.state.api_key_authenticated = bool(configured_key)
