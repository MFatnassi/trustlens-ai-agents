"""
End-to-end test for the TrustLens orchestrator.

Runs the full pipeline (Router -> Scout -> Verifier -> Scorer) on a single
real input and prints the complete API response.

Usage:
    cd backend
    python -m tests.test_orchestrator_e2e

    # Or with a custom input:
    python -m tests.test_orchestrator_e2e "Is this true: the new vaccine causes infertility?"
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from orchestrator import analyze  # noqa: E402


DEFAULT_INPUT = (
    "Breaking news from the Associated Press -- The World Health Organization "
    "announced today that a new variant of the H5N1 avian influenza virus has "
    "been detected in three countries across Southeast Asia. Health officials "
    "are urging poultry farmers to implement strict biosecurity measures."
)


async def main():
    user_input = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT

    print("=" * 70)
    print("TrustLens -- End-to-End Pipeline Test")
    print("=" * 70)
    print(f"\nInput ({len(user_input)} chars):")
    print(f"  {user_input[:120]}...")

    start = time.time()
    result = await analyze(user_input)
    elapsed = time.time() - start

    print(f"\nPipeline completed in {elapsed:.1f}s")
    print(f"Detected mode: {result['mode']}")
    print(f"Sources used: {len(result['sources_used'])}")

    if result["mode"] == "public":
        print(f"Trust score: {result['result']['trust_score']}/100")
        print(f"\nExplanation:")
        for line in result["result"]["explanation"].split("\n"):
            print(f"  {line}")
    else:
        print(f"\nBrief:")
        for line in result["result"]["brief"].split("\n"):
            print(f"  {line}")

    print(f"\nSources used:")
    for i, s in enumerate(result["sources_used"][:10], 1):
        print(f"  [{i}] {s['title'][:60]} - {s['url'][:70]}")
    if len(result["sources_used"]) > 10:
        print(f"  ... and {len(result['sources_used']) - 10} more")

    # Validate API contract (Section 7)
    print("\n--- API Contract Validation ---")
    checks = [
        ("'mode' field exists", "mode" in result),
        ("'result' field exists", "result" in result),
        ("'sources_used' field exists", "sources_used" in result),
        ("mode is 'public' or 'newsroom'", result.get("mode") in ("public", "newsroom")),
        ("sources_used has url+title", all("url" in s and "title" in s for s in result.get("sources_used", []))),
    ]
    if result["mode"] == "public":
        checks.append(("result has trust_score", "trust_score" in result.get("result", {})))
        checks.append(("result has explanation", "explanation" in result.get("result", {})))
        checks.append(("trust_score is 0-100", 0 <= result.get("result", {}).get("trust_score", -1) <= 100))
    else:
        checks.append(("result has brief", "brief" in result.get("result", {})))

    all_pass = True
    for label, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_pass = False
        print(f"  {status} {label}")

    print("\n" + "=" * 70)
    if all_pass:
        print("All checks passed. Pipeline is working end-to-end.")
    else:
        print("Some checks failed -- review output above.")
    print("=" * 70)

    # Dump full JSON for inspection
    print("\n--- Full JSON response ---")
    # Truncate explanation/brief for readability
    output_copy = json.loads(json.dumps(result))
    if "explanation" in output_copy.get("result", {}):
        exp = output_copy["result"]["explanation"]
        if len(exp) > 500:
            output_copy["result"]["explanation"] = exp[:500] + "..."
    if "brief" in output_copy.get("result", {}):
        br = output_copy["result"]["brief"]
        if len(br) > 1000:
            output_copy["result"]["brief"] = br[:1000] + "..."
    print(json.dumps(output_copy, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
