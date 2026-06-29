"""
Standalone test script for the Router Agent.

Runs 3 sample inputs and prints the classification output for visual
verification. Requires GOOGLE_API_KEY to be set in a .env file at the
project root (or as an environment variable).

Usage:
    cd backend
    python -m tests.test_router_agent
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

# Load .env from the project root (two levels up from this file)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from agents.router_agent import router_agent  # noqa: E402

# ---------------------------------------------------------------------------
# Three test cases — one per classification scenario
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "label": "1. Long article text (expected: public)",
        "input": (
            "Breaking news from the Associated Press — The World Health Organization "
            "announced today that a new variant of the H5N1 avian influenza virus has "
            "been detected in three countries across Southeast Asia. Health officials "
            "are urging poultry farmers to implement strict biosecurity measures. "
            "According to Dr. Maria Van Kerkhove, the WHO's technical lead on "
            "influenza, 'while the risk to the general public remains low, we are "
            "closely monitoring the situation and working with national authorities "
            "to ensure rapid containment.' The variant, tentatively named clade "
            "2.3.4.4b.1, shows mutations in the hemagglutinin protein that may "
            "affect transmissibility between birds, though there is no evidence yet "
            "of sustained human-to-human transmission."
        ),
    },
    {
        "label": "2. Single URL (expected: public)",
        "input": "https://www.reuters.com/world/middle-east/some-breaking-news-article-2026",
    },
    {
        "label": "3. Short topic / keywords (expected: newsroom)",
        "input": "monitoring election fraud claims",
    },
]


async def run_test(text: str) -> dict:
    """Send a single input to the Router Agent and return the parsed result."""
    runner = InMemoryRunner(agent=router_agent, app_name="trustlens_test")
    session = await runner.session_service.create_session(
        app_name="trustlens_test", user_id="test_user"
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=text)],
    )

    # Iterate over events until we get the final response
    result_text = ""
    for event in runner.run(
        user_id="test_user", session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            result_text = event.content.parts[0].text
            break

    return json.loads(result_text)


async def main():
    print("=" * 60)
    print("Router Agent — Classification Tests")
    print("=" * 60)

    for case in TEST_CASES:
        print(f"\n--- {case['label']} ---")
        print(f"Input (first 80 chars): {case['input'][:80]}...")
        try:
            result = await run_test(case["input"])
            print(json.dumps(result, indent=2))
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

    print("\n" + "=" * 60)
    print("All tests completed. Review the outputs above.")
    print("=" * 60)


async def classify(query: str):
    """Quick helper — classify a single query and print the result.

    Usage:
        cd backend
        python -m tests.test_router_agent "Is this true: the new vaccine causes infertility?"
    """
    print(f"Query: {query}")
    result = await run_test(query)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query mode: python -m tests.test_router_agent "your query here"
        asyncio.run(classify(sys.argv[1]))
    else:
        # Full test suite
        asyncio.run(main())
