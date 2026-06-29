"""
Standalone test script for the Scorer / Final Writer Agent.

Four test cases:
  1. Public mode -- H5N1 article: check trust score + explanation.
  2. Newsroom mode -- election fraud: check structured brief with contradictions.
  3. Gibberish -- zero facts: verify low score and honest explanation.
  4. Refuted claim -- "Lyon is the capital of France": verify low score + false verdict.

Usage:
    cd backend
    python -m tests.test_scorer_agent
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from agents.scorer_agent import run_scorer, compute_trust_score  # noqa: E402


# ---------------------------------------------------------------------------
# Test content
# ---------------------------------------------------------------------------

H5N1_ARTICLE = (
    "Breaking news from the Associated Press -- The World Health Organization "
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
)

ELECTION_TOPIC = "monitor election fraud claims"

GIBBERISH_CONTENT = "xqzjklw9384 vbnmqp fhrtt zwwp83 kkrtnn claims something happened."


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent


def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / name
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _load_sources(name: str) -> list[dict]:
    path = FIXTURES_DIR / name
    if path.exists():
        with open(path) as f:
            return json.load(f).get("sources", [])
    return []


# ---------------------------------------------------------------------------
# Main test suite
# ---------------------------------------------------------------------------

async def main():
    # Load fixtures
    verifier_public = _load_fixture("_fixtures_verifier_public.json")
    verifier_newsroom = _load_fixture("_fixtures_verifier_newsroom.json")
    verifier_gibberish = _load_fixture("_fixtures_verifier_gibberish.json")
    sources_public = _load_sources("_fixtures_public.json")
    sources_newsroom = _load_sources("_fixtures_newsroom.json")
    gibberish_sources = [
        {"url": "https://www.flightaware.com", "title": "FlightAware", "snippet": "Track flights.", "published_date": None, "domain_reputation_hint": None},
        {"url": "https://fahertybrand.com", "title": "Faherty Brand", "snippet": "Summer collection.", "published_date": None, "domain_reputation_hint": None},
    ]

    print("=" * 70)
    print("Scorer Agent -- Final Output Tests")
    print("=" * 70)

    # ------------------------------------------------------------------
    # TEST 1: Public mode -- H5N1 article
    # ------------------------------------------------------------------
    print("\n--- Test 1: Public mode -- H5N1 article ---")
    score_1 = compute_trust_score(verifier_public)
    print(f"  Computed trust score: {score_1}/100")
    print(f"  (facts={len(verifier_public.get('facts', []))}, "
          f"unsupported={len(verifier_public.get('unsupported_claims', []))}, "
          f"contradictions={len(verifier_public.get('contradictions', []))})")

    result_1 = await run_scorer("public", H5N1_ARTICLE, verifier_public, sources_public)

    print(f"\n  Trust score in output: {result_1['result']['trust_score']}/100")
    print(f"  Sources used: {len(result_1['sources_used'])}")
    print(f"\n  Explanation:\n")
    for line in result_1["result"]["explanation"].split("\n"):
        print(f"    {line}")

    # Verify score is reasonable: with 3 facts and 6 unsupported, score < 50
    if result_1["result"]["trust_score"] < 50:
        print(f"\n  [PASS] Score {result_1['result']['trust_score']} is appropriately low for mostly-unsupported content")
    else:
        print(f"\n  [FAIL] Score {result_1['result']['trust_score']} seems too high for 3 facts vs 6 unsupported claims")

    # Verify sources_used has url + title
    has_url_and_title = all("url" in s and "title" in s for s in result_1["sources_used"])
    if has_url_and_title:
        print("  [PASS] All sources_used entries have url and title")
    else:
        print("  [FAIL] Some sources_used entries missing url or title")

    # ------------------------------------------------------------------
    # TEST 2: Newsroom mode -- election fraud
    # ------------------------------------------------------------------
    print("\n--- Test 2: Newsroom mode -- election fraud ---")
    result_2 = await run_scorer("newsroom", ELECTION_TOPIC, verifier_newsroom, sources_newsroom)

    print(f"  Sources used: {len(result_2['sources_used'])}")
    print(f"\n  Brief:\n")
    for line in result_2["result"]["brief"].split("\n"):
        print(f"    {line}")

    # Check that contradictions section exists in the brief
    brief_lower = result_2["result"]["brief"].lower()
    has_contradiction_section = "contradiction" in brief_lower
    if has_contradiction_section:
        print("\n  [PASS] Contradictions section present in brief")
    else:
        print("\n  [FAIL] No contradictions section found in brief")

    # Check all four required sections
    required_sections = ["summary", "reliable", "contradiction", "editorial"]
    found_sections = [s for s in required_sections if s in brief_lower]
    print(f"  [INFO] Sections found: {found_sections} (expected all 4)")

    # ------------------------------------------------------------------
    # TEST 3: Gibberish -- zero facts, should score very low
    # ------------------------------------------------------------------
    print("\n--- Test 3: Gibberish -- zero verifiable facts ---")
    score_3 = compute_trust_score(verifier_gibberish)
    print(f"  Computed trust score: {score_3}/100")

    result_3 = await run_scorer("public", GIBBERISH_CONTENT, verifier_gibberish, gibberish_sources)

    print(f"\n  Trust score in output: {result_3['result']['trust_score']}/100")
    print(f"\n  Explanation:\n")
    for line in result_3["result"]["explanation"].split("\n"):
        print(f"    {line}")

    # Score must be very low (0-19 range)
    if result_3["result"]["trust_score"] <= 19:
        print(f"\n  [PASS] Score {result_3['result']['trust_score']} is appropriately near-zero")
    else:
        print(f"\n  [FAIL] Score {result_3['result']['trust_score']} too high for zero-fact content")

    # Explanation should mention insufficient/unverifiable
    explanation_lower = result_3["result"]["explanation"].lower()
    honest_terms = ["insufficient", "unverif", "cannot", "no verif", "not verif", "no fact", "unable"]
    is_honest = any(t in explanation_lower for t in honest_terms)
    if is_honest:
        print("  [PASS] Explanation honestly describes lack of verifiable information")
    else:
        print("  [WARN] Explanation may not clearly state content is unverifiable (check manually)")

    # ------------------------------------------------------------------
    # TEST 4: Refuted claim -- "Lyon is the capital of France"
    # ------------------------------------------------------------------
    print("\n--- Test 4: Refuted claim -- 'Lyon is the capital of France' ---")

    lyon_content = "Lyon is the capital of France and the largest city in the country."
    lyon_verifier_output = {
        "facts": [],
        "opinions": [],
        "unsupported_claims": [],
        "refuted_claims": [
            {
                "claim": "Lyon is the capital of France",
                "refuted_by": ["https://en.wikipedia.org/wiki/France", "https://en.wikipedia.org/wiki/Paris"],
                "correct_info": "Paris is the capital and largest city of France."
            },
            {
                "claim": "Lyon is the largest city in France",
                "refuted_by": ["https://en.wikipedia.org/wiki/Paris"],
                "correct_info": "Paris is the largest city of France with over 2 million residents."
            }
        ],
        "contradictions": []
    }
    lyon_sources = [
        {"url": "https://en.wikipedia.org/wiki/France", "title": "France - Wikipedia", "snippet": "Capital is Paris."},
        {"url": "https://en.wikipedia.org/wiki/Paris", "title": "Paris - Wikipedia", "snippet": "Paris is the capital."},
    ]

    score_4 = compute_trust_score(lyon_verifier_output)
    print(f"  Computed trust score: {score_4}/100")

    result_4 = await run_scorer("public", lyon_content, lyon_verifier_output, lyon_sources)

    print(f"\n  Trust score in output: {result_4['result']['trust_score']}/100")
    print(f"  Input verdict: {result_4['result']['input_verdict']}")
    print(f"\n  Explanation:\n")
    for line in result_4["result"]["explanation"].split("\n"):
        print(f"    {line}")

    # Score must be very low (capped at 15 due to refuted claims)
    if result_4["result"]["trust_score"] <= 15:
        print(f"\n  [PASS] Score {result_4['result']['trust_score']} is correctly low for refuted claims (cap at 15)")
    else:
        print(f"\n  [FAIL] Score {result_4['result']['trust_score']} is too high -- refuted claims should cap at 15")

    # Verdict must be "false"
    if result_4["result"]["input_verdict"] == "false":
        print("  [PASS] Verdict is 'false' -- correct for refuted claims")
    else:
        print(f"  [FAIL] Verdict is '{result_4['result']['input_verdict']}' -- expected 'false' for refuted claims")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("All tests completed. Review outputs above for correctness.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
