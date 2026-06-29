"""
Standalone test script for the Scout Agent.

Runs 3 test cases that simulate Router Agent outputs being fed into the
Scout Agent. Prints sources found for visual verification.

Usage:
    cd backend
    python -m tests.test_scout_agent

    # Or test a single custom query:
    python -m tests.test_scout_agent "public" "Verify vaccine infertility claim"
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from agents.scout_agent import run_scout  # noqa: E402

# ---------------------------------------------------------------------------
# Three test cases simulating Router Agent outputs
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "label": "1. Public mode — long article about H5N1 (from Router test case 1)",
        "mode": "public",
        "normalized_query": "Verify report on new H5N1 avian influenza variant in Southeast Asia",
    },
    {
        "label": "2. Newsroom mode — election fraud monitoring (from Router test case 3)",
        "mode": "newsroom",
        "normalized_query": "monitor election fraud claims",
    },
    {
        "label": "3. Edge case — semi-nonsense (may return tangential results)",
        "mode": "public",
        "normalized_query": "zqxjkw7 plmtv9 brnfhd3 qvwxyz nonsense claim 98765",
    },
    {
        "label": "4. Edge case — pure random gibberish (should return empty or near-empty)",
        "mode": "public",
        "normalized_query": "xqzjklw9384 vbnmqp fhrtt zwwp83 kkrtnn",
    },
]


def _print_sources(result: dict):
    """Pretty-print the sources from a Scout Agent result."""
    sources = result.get("sources", [])
    print(f"  Found {len(sources)} source(s)")
    for i, src in enumerate(sources, 1):
        print(f"\n  [{i}] {src['title']}")
        print(f"      URL: {src['url']}")
        print(f"      Snippet: {src['snippet'][:120]}...")
    if not sources:
        print("  (no sources found — this is expected for nonsense queries)")


async def main():
    print("=" * 60)
    print("Scout Agent — Source Collection Tests")
    print("=" * 60)

    for case in TEST_CASES:
        print(f"\n--- {case['label']} ---")
        print(f"  Mode: {case['mode']}")
        print(f"  Query: {case['normalized_query']}")
        try:
            result = await run_scout(case["mode"], case["normalized_query"])
            _print_sources(result)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)

    print("\n" + "=" * 60)
    print("All tests completed. Review the outputs above.")
    print("=" * 60)


async def classify_and_scout(mode: str, query: str):
    """Quick helper — run the Scout Agent on a single input.

    Usage:
        cd backend
        python -m tests.test_scout_agent "public" "Is the vaccine safe?"
    """
    print(f"Mode: {mode}")
    print(f"Query: {query}")
    result = await run_scout(mode, query)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3:
        # Single query mode: python -m tests.test_scout_agent "public" "query"
        asyncio.run(classify_and_scout(sys.argv[1], sys.argv[2]))
    else:
        # Full test suite
        asyncio.run(main())
