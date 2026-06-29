"""
ADK Orchestrator -- Section 3 & 8 of the project specification

Chains the four agents in sequence based on the detected mode:

  User input
      |
      v
  1. Router Agent   -- classifies input as "public" or "newsroom"
      |
      v
  2. Scout Agent    -- collects sources via Tavily MCP search
      |
      v
  3. Verifier Agent -- cross-checks content against sources
      |
      v
  4. Scorer Agent   -- produces the final output (score or brief)

Output matches the Section 7 API contract exactly:
  {
    "mode": "public" | "newsroom",
    "result": { ... },
    "sources_used": [{"url": "string", "title": "string"}]
  }
"""

import asyncio
import json
import logging

from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger("trustlens.orchestrator")

# Load .env from the project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from agents.router_agent import router_agent  # noqa: E402
from agents.scout_agent import run_scout  # noqa: E402
from agents.verifier_agent import run_verifier  # noqa: E402
from agents.scorer_agent import run_scorer  # noqa: E402

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402


async def analyze(user_input: str) -> dict:
    """Run the full TrustLens pipeline on a user input.

    This is the main entry point for the backend. It chains all four
    agents and returns the final result matching the Section 7 API contract.

    Args:
        user_input: Raw text from the user (article, URL, topic, etc.)

    Returns:
        Dict with keys: mode, result, sources_used
    """

    # ----- Step 1: Router Agent -----
    # Classify the input as "public" (fact-check) or "newsroom" (monitoring).
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_input)],
    )

    router_output = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            runner = InMemoryRunner(agent=router_agent, app_name="trustlens")
            session = await runner.session_service.create_session(
                app_name="trustlens", user_id="user"
            )
            router_result_text = ""
            for event in runner.run(
                user_id="user", session_id=session.id, new_message=message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    router_result_text = event.content.parts[0].text
                    break

            if not router_result_text.strip():
                raise ValueError("Router returned empty response")

            router_output = json.loads(router_result_text)
            break
        except Exception as e:
            error_msg = str(e)
            is_transient = any(k in error_msg for k in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "empty response"))
            if is_transient and attempt < max_retries - 1:
                wait = 20 if "429" in error_msg else 2 ** (attempt + 1)
                logger.warning("Router attempt %d failed (%s), retrying in %ds...", attempt + 1, error_msg[:80], wait)
                await asyncio.sleep(wait)
            else:
                raise
    mode = router_output["mode"]
    normalized_query = router_output["normalized_query"]
    detected_language = router_output.get("detected_language", "en")

    # ----- Step 2: Scout Agent -----
    # Collect sources via Tavily MCP search, adapted to the mode.
    scout_output = await run_scout(mode, normalized_query)
    sources = scout_output["sources"]

    # ----- Step 3: Verifier Agent -----
    # Cross-check the original content against the collected sources.
    verifier_output = await run_verifier(user_input, sources, mode)

    # ----- Step 4: Scorer Agent -----
    # Produce the final output (trust score or journalistic brief).
    final_output = await run_scorer(mode, user_input, verifier_output, sources)

    # Add detected_language to the response
    final_output["detected_language"] = detected_language

    return final_output
