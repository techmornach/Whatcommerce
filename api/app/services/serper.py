"""Serper.dev Google search API — used by agents for web grounding (no Playwright MCP)."""

from typing import Any

import httpx

from app.core.config import get_settings

SERPER_SEARCH_URL = "https://google.serper.dev/search"


async def serper_search(query: str, num: int = 8) -> dict[str, Any]:
    settings = get_settings()
    if not settings.serper_api_key:
        raise RuntimeError("SERPER_API_KEY is not set")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SERPER_SEARCH_URL,
            headers={
                "X-API-KEY": settings.serper_api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": num},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
