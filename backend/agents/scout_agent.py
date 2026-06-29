"""
Scout Agent — Section 3.2 of the project specification

Collects relevant sources via the Tavily MCP search server.
Behavior adapts based on the mode received from the Router Agent:

  - "public" mode:  1–3 targeted searches to verify a specific piece of
                    content (e.g. searching the claim, key quotes, author).
  - "newsroom" mode: 3–5 broad searches across multiple angles of a topic,
                     with varied phrasings to maximize source diversity.

The agent uses an LLM (Gemini Flash Lite) to generate smart search queries
from the normalized_query, then executes them via the MCP client.

Output matches the exact JSON schema from Section 3.2:
  { "sources": [{ "url", "title", "snippet", "published_date", "domain_reputation_hint" }] }
"""

import asyncio
import json

from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from mcp_client.search_mcp_client import TavilyMCPClient


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SearchQueries(BaseModel):
    """Output schema for the query-generation LLM step."""
    queries: list[str] = Field(
        description="List of search queries to execute."
    )


class Source(BaseModel):
    """A single source matching the Section 3.2 schema."""
    url: str
    title: str
    snippet: str
    published_date: str | None = None
    domain_reputation_hint: str | None = None


class ScoutResult(BaseModel):
    """The Scout Agent's final output."""
    sources: list[Source] = []


# ---------------------------------------------------------------------------
# Query generation agent
# ---------------------------------------------------------------------------
# This lightweight LLM agent generates search queries tailored to the mode.
# It does NOT perform the search itself — just decides *what* to search for.
# Using an LLM here lets us generate smarter, more varied queries than
# simple string manipulation would allow.

QUERY_GEN_INSTRUCTION = """\
You are a search-query generator for a fact-checking system called TrustLens.

Given a MODE and a NORMALIZED_QUERY, generate a list of web search queries.

## Rules by mode:

### MODE = "public" (verifying a specific claim or article)
Generate 1 to 3 targeted queries:
  - Query 1: Search the core claim or article title directly.
  - Query 2: Search for key entities (people, organizations, dates) mentioned.
  - Query 3 (if applicable): Search for fact-checks or debunks of the claim.
Keep queries specific and fact-oriented.

### MODE = "newsroom" (broad topic monitoring)
Generate 3 to 5 diverse queries:
  - Query 1: The topic stated directly.
  - Query 2: The topic with a different angle (e.g. causes, consequences).
  - Query 3: The topic + "latest news" or "recent developments".
  - Query 4: A contrary or skeptical phrasing (to find opposing views).
  - Query 5 (if applicable): The topic + a specific geographic or temporal scope.
Vary phrasing to maximize source diversity and capture multiple viewpoints.

## Output
Return ONLY the JSON object with a "queries" array. No extra text.
"""

query_gen_agent = LlmAgent(
    name="query_generator",
    model="gemini-3.1-flash-lite",
    description="Generates search queries adapted to the analysis mode.",
    instruction=QUERY_GEN_INSTRUCTION,
    output_schema=SearchQueries,
)


# ---------------------------------------------------------------------------
# Helper: run the query-generation agent
# ---------------------------------------------------------------------------

async def _generate_queries(mode: str, normalized_query: str) -> list[str]:
    """Use the LLM to generate search queries based on mode and query."""
    runner = InMemoryRunner(agent=query_gen_agent, app_name="trustlens_scout")
    session = await runner.session_service.create_session(
        app_name="trustlens_scout", user_id="scout"
    )

    # Format the input so the LLM knows the mode and query
    prompt = f"MODE: {mode}\nNORMALIZED_QUERY: {normalized_query}"
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    result_text = ""
    for event in runner.run(user_id="scout", session_id=session.id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            result_text = event.content.parts[0].text
            break

    parsed = json.loads(result_text)
    return parsed.get("queries", [])


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _deduplicate_sources(sources: list[dict]) -> list[dict]:
    """Remove duplicate sources based on URL."""
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for source in sources:
        url = source.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(source)
    return unique


# ---------------------------------------------------------------------------
# Main Scout Agent function
# ---------------------------------------------------------------------------

async def run_scout(mode: str, normalized_query: str) -> dict:
    """Execute the Scout Agent pipeline.

    1. Generate search queries using the LLM (adapted to mode).
    2. Execute each query via the Tavily MCP server.
    3. Deduplicate and return results in the Section 3.2 schema.

    Args:
        mode: "public" or "newsroom" (from the Router Agent).
        normalized_query: Concise restatement of user intent (from Router).

    Returns:
        Dict matching Section 3.2: {"sources": [{"url", "title", "snippet", ...}]}
        Returns {"sources": []} if no results found — never fabricates sources.
    """
    # Step 1: Generate search queries via LLM
    queries = await _generate_queries(mode, normalized_query)

    # Safety: enforce query count limits per mode
    if mode == "public":
        queries = queries[:3]   # 1–3 targeted searches
    else:
        queries = queries[:5]   # 3–5 broad searches

    # Step 2: Execute searches via the Tavily MCP server
    # We use the context manager to keep a single MCP connection open
    # across all queries (avoids re-spawning npx for each search).
    all_sources: list[dict] = []
    async with TavilyMCPClient() as client:
        for query in queries:
            results = await client.search(query, max_results=5)
            all_sources.extend(results)

    # Step 3: Deduplicate by URL and cap results
    unique_sources = _deduplicate_sources(all_sources)

    # Newsroom mode can generate many sources (5 queries x 5 results).
    # Cap at 15 to keep the Verifier Agent's input manageable.
    # Prioritize domain variety: the dedup already ensures unique URLs,
    # and the varied search queries naturally produce diverse domains.
    if mode == "newsroom":
        unique_sources = unique_sources[:15]

    return {"sources": unique_sources}
