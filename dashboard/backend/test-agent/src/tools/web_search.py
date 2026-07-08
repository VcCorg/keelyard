"""Web search tool."""

import httpx

async def web_search(query: str, num_results: int = 5) -> list:
    """Search the web for information."""
    # Placeholder - implement with actual search API
    return [{"title": "Result", "url": "https://example.com", "snippet": query}]
