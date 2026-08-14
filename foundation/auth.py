from __future__ import annotations

from fastapi import Header, HTTPException

from .config import get_settings


async def require_app(
    x_app_id: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> str:
    settings = get_settings()
    if settings.foundation_mode == "mock" and not settings.api_keys:
        return x_app_id or "development"
    if not x_app_id or settings.api_keys.get(x_app_id) != x_api_key:
        raise HTTPException(401, "Invalid application credentials")
    return x_app_id

