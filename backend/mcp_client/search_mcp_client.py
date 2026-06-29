"""
Search MCP Client — Section 5 of the project specification

Connects to the Tavily MCP Server for web search via the MCP protocol.
This is a real MCP client-server integration (not a raw API call), which
validates the "MCP Server" course concept required by the capstone.

Why Tavily:
  - Free tier: 1,000 API credits/month, no credit card required.
  - Works in "keyless mode" for basic searches (limited rate).
  - Official MCP server available via npx (tavily-mcp).

Environment variable needed:
  TAVILY_API_KEY  — get one free at https://app.tavily.com

Usage:
    async with TavilyMCPClient() as client:
        results = await client.search("H5N1 avian influenza 2026")

    # Or standalone convenience function:
    results = await search("H5N1 avian influenza 2026", max_results=5)
"""

import os
import re
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------------------------------------------------------------------
# Environment variables required to spawn npx on Windows and Unix
# ---------------------------------------------------------------------------
# npx needs PATH to find node, and Windows needs certain system env vars
# (SYSTEMROOT, APPDATA, etc.) for subprocesses to function correctly.

_PASSTHROUGH_ENV_KEYS = (
    "PATH", "SYSTEMROOT", "APPDATA", "LOCALAPPDATA",
    "USERPROFILE", "TEMP", "TMP", "HOME", "HOMEDRIVE", "HOMEPATH",
)


def _build_subprocess_env() -> dict[str, str]:
    """Build the environment dict for the npx subprocess."""
    env = {"TAVILY_API_KEY": os.environ.get("TAVILY_API_KEY", "")}
    for key in _PASSTHROUGH_ENV_KEYS:
        val = os.environ.get(key)
        if val:
            env[key] = val
    return env


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------
# Tavily MCP returns plain-text blocks in this format:
#   Title: <title>
#   URL: <url>
#   Content: <snippet text>
#
# We parse these blocks into the source schema defined in Section 3.2.

def _parse_tavily_text(text: str) -> list[dict]:
    """Parse Tavily MCP plain-text response into structured source dicts."""
    sources: list[dict] = []

    # Split on "Title: " to isolate each result block.
    # The first chunk is the header ("Detailed Results:\n\n") — skip it.
    blocks = re.split(r"(?=Title: )", text)

    for block in blocks:
        block = block.strip()
        if not block.startswith("Title: "):
            continue

        # Extract fields using regex
        title_match = re.match(r"Title: (.+)", block)
        url_match = re.search(r"URL: (.+)", block)
        # Content may span multiple lines — capture everything after "Content: "
        content_match = re.search(r"Content: (.+)", block, re.DOTALL)

        sources.append({
            "url": url_match.group(1).strip() if url_match else "",
            "title": title_match.group(1).strip() if title_match else "",
            "snippet": content_match.group(1).strip() if content_match else "",
            "published_date": None,   # Tavily keyless mode doesn't return dates
            "domain_reputation_hint": None,  # To be enriched later if needed
        })

    return sources


# ---------------------------------------------------------------------------
# MCP Client class
# ---------------------------------------------------------------------------

class TavilyMCPClient:
    """Async context manager that maintains a connection to the Tavily MCP server.

    Keeps the npx subprocess alive for the duration of the context, so
    multiple searches reuse the same connection (no re-spawning overhead).
    """

    def __init__(self):
        self._exit_stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "TavilyMCPClient":
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "tavily-mcp@latest"],
            env=_build_subprocess_env(),
        )
        # Open the stdio transport and MCP session, keep them alive
        streams = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(*streams)
        )
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info):
        await self._exit_stack.aclose()
        self._session = None

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Run a web search via the Tavily MCP server.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return (default 5).

        Returns:
            A list of source dicts matching the Section 3.2 schema:
            [{"url", "title", "snippet", "published_date", "domain_reputation_hint"}]
            Returns an empty list if zero results are found — never raises
            an unhandled exception and never fabricates a fake source.
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with TavilyMCPClient() as client:'")

        try:
            result = await self._session.call_tool(
                "tavily_search",
                arguments={"query": query, "max_results": max_results},
            )

            # Tavily MCP returns TextContent with plain-text results
            all_sources: list[dict] = []
            for content in result.content:
                if hasattr(content, "text"):
                    parsed = _parse_tavily_text(content.text)
                    all_sources.extend(parsed)

            return all_sources[:max_results]

        except Exception:
            # Safety: never crash, never fabricate — return empty list
            return []


# ---------------------------------------------------------------------------
# Standalone convenience function
# ---------------------------------------------------------------------------

async def search(query: str, max_results: int = 5) -> list[dict]:
    """One-shot search: opens a connection, searches, and closes.

    Convenient for testing, but prefer TavilyMCPClient context manager
    when running multiple searches (avoids re-spawning npx each time).
    """
    async with TavilyMCPClient() as client:
        return await client.search(query, max_results)
