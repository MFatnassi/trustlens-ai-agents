"""
Standalone test script for the Verifier Agent.

Tests the most safety-critical component of TrustLens: the agent that
cross-checks content against sources, with strict anti-hallucination
constraints.

Six test cases:
  1. Public mode --H5N1 article with real Scout Agent sources.
  2. Newsroom mode --election fraud sources, check for contradictions.
  3. Fabricated claim --a plausible statistic NOT in any source snippet.
  4. Gibberish sources --irrelevant sources should not support any claim.
  5. Refuted claim --"Lyon is the capital of France" should be refuted, not unsupported.
  6. URL hallucination check --assert every URL in output exists in input.

Usage:
    cd backend
    python -m tests.test_verifier_agent
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from agents.verifier_agent import run_verifier  # noqa: E402


# ---------------------------------------------------------------------------
# Test content
# ---------------------------------------------------------------------------

H5N1_ARTICLE = (
    "Breaking news from the Associated Press --The World Health Organization "
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

# Fabricated claim: sounds plausible but is NOT in any source snippet.
# This tests the anti-hallucination constraint.
FABRICATED_CLAIM_ARTICLE = (
    "According to a recent WHO report, H5N1 avian influenza has been detected "
    "in Southeast Asia. Additionally, Dr. Jean-Pierre Morel, head of the WHO "
    "Pandemic Response Unit, confirmed that exactly 847 poultry farms across "
    "Vietnam were quarantined in the first week of June 2026 alone, making it "
    "the largest single-week quarantine in the history of avian flu response."
)

GIBBERISH_CONTENT = "xqzjklw9384 vbnmqp fhrtt zwwp83 kkrtnn claims something happened."

ELECTION_TOPIC = "monitor election fraud claims"


# ---------------------------------------------------------------------------
# Fixtures: load real Scout Agent outputs saved during scout tests
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent


def _load_fixture(name: str) -> list[dict]:
    """Load a fixture file, or return minimal placeholder if not found."""
    path = FIXTURES_DIR / name
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        return data.get("sources", [])
    # Fallback: minimal sources for CI or first-run scenarios
    return []


def _make_gibberish_sources() -> list[dict]:
    """Fabricate irrelevant sources that have nothing to do with any real claim."""
    return [
        {
            "url": "https://www.flightaware.com",
            "title": "FlightAware - Flight Tracker",
            "snippet": "Track flights in real time. FlightAware provides live flight data.",
            "published_date": None,
            "domain_reputation_hint": None,
        },
        {
            "url": "https://fahertybrand.com",
            "title": "Faherty Brand - Official Site",
            "snippet": "Free shipping on orders over $150. Summer collection now available.",
            "published_date": None,
            "domain_reputation_hint": None,
        },
        {
            "url": "https://www.fay.com/us-en/track-your-order",
            "title": "Track your order - Fay",
            "snippet": "Enter your Order Number to see the list of products you have ordered.",
            "published_date": None,
            "domain_reputation_hint": None,
        },
    ]


# ---------------------------------------------------------------------------
# URL hallucination assertion (Test 5)
# ---------------------------------------------------------------------------

def assert_no_hallucinated_urls(result: dict, input_source_urls: set[str]) -> list[str]:
    """Check that every URL referenced in the Verifier output exists in the input sources.

    Returns a list of violations (empty = passed).
    """
    violations = []

    # Check facts → supported_by URLs
    for fact in result.get("facts", []):
        for url in fact.get("supported_by", []):
            if url not in input_source_urls:
                violations.append(f"HALLUCINATED URL in facts: {url}")

    # Check refuted_claims → refuted_by URLs
    for refuted in result.get("refuted_claims", []):
        for url in refuted.get("refuted_by", []):
            if url not in input_source_urls:
                violations.append(f"HALLUCINATED URL in refuted_claims: {url}")

    # Check contradictions → source_a and source_b URLs
    for contradiction in result.get("contradictions", []):
        for key in ("source_a", "source_b"):
            url = contradiction.get(key, "")
            if url and url not in input_source_urls:
                violations.append(f"HALLUCINATED URL in contradictions.{key}: {url}")

    return violations


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def _print_result(result: dict):
    """Pretty-print Verifier output."""
    facts = result.get("facts", [])
    opinions = result.get("opinions", [])
    unsupported = result.get("unsupported_claims", [])
    refuted = result.get("refuted_claims", [])
    contradictions = result.get("contradictions", [])

    print(f"  Facts ({len(facts)}):")
    for f in facts:
        urls = ", ".join(f["supported_by"][:2])
        suffix = "..." if len(f["supported_by"]) > 2 else ""
        print(f"    [{f['confidence']}] {f['claim'][:100]}")
        print(f"           Sources: {urls}{suffix}")

    print(f"  Opinions ({len(opinions)}):")
    for o in opinions:
        print(f"    - {o[:120]}")

    print(f"  Unsupported claims ({len(unsupported)}):")
    for u in unsupported:
        print(f"    - {u[:120]}")

    print(f"  Refuted claims ({len(refuted)}):")
    for r in refuted:
        urls = ", ".join(r["refuted_by"][:2])
        print(f"    - {r['claim'][:100]}")
        print(f"      Correct: {r['correct_info'][:100]}")
        print(f"      Sources: {urls}")

    print(f"  Contradictions ({len(contradictions)}):")
    for c in contradictions:
        print(f"    Point: {c['point'][:100]}")
        print(f"      A: {c['source_a'][:60]} -> {c['position_a'][:80]}")
        print(f"      B: {c['source_b'][:60]} -> {c['position_b'][:80]}")


# ---------------------------------------------------------------------------
# Main test suite
# ---------------------------------------------------------------------------

async def main():
    public_sources = _load_fixture("_fixtures_public.json")
    newsroom_sources = _load_fixture("_fixtures_newsroom.json")
    gibberish_sources = _make_gibberish_sources()

    # Collect all input URLs for the hallucination check across all tests
    all_url_violations = []

    print("=" * 70)
    print("Verifier Agent --Safety & Correctness Tests")
    print("=" * 70)

    # ------------------------------------------------------------------
    # TEST 1: Public mode --H5N1 article with real sources
    # ------------------------------------------------------------------
    print("\n--- Test 1: Public mode --H5N1 article ---")
    print(f"  Content: {H5N1_ARTICLE[:80]}...")
    print(f"  Sources provided: {len(public_sources)}")
    r1 = await run_verifier(H5N1_ARTICLE, public_sources, "public")
    _print_result(r1)

    input_urls_1 = {s["url"] for s in public_sources}
    violations_1 = assert_no_hallucinated_urls(r1, input_urls_1)
    all_url_violations.extend(violations_1)

    # ------------------------------------------------------------------
    # TEST 2: Newsroom mode --election fraud, check for contradictions
    # ------------------------------------------------------------------
    print("\n--- Test 2: Newsroom mode --election fraud ---")
    print(f"  Topic: {ELECTION_TOPIC}")
    print(f"  Sources provided: {len(newsroom_sources)}")
    r2 = await run_verifier(ELECTION_TOPIC, newsroom_sources, "newsroom")
    _print_result(r2)

    input_urls_2 = {s["url"] for s in newsroom_sources}
    violations_2 = assert_no_hallucinated_urls(r2, input_urls_2)
    all_url_violations.extend(violations_2)

    # ------------------------------------------------------------------
    # TEST 3: CRITICAL --Fabricated claim not in any source
    # ------------------------------------------------------------------
    print("\n--- Test 3: CRITICAL --Fabricated claim detection ---")
    print("  Content includes a fabricated statistic: '847 poultry farms'")
    print("  and a made-up person: 'Dr. Jean-Pierre Morel'")
    print(f"  Sources provided: {len(public_sources)} (same H5N1 sources)")
    r3 = await run_verifier(FABRICATED_CLAIM_ARTICLE, public_sources, "public")
    _print_result(r3)

    # Check: the fabricated details should be in unsupported_claims
    unsupported_text = " ".join(r3.get("unsupported_claims", []))
    facts_text = " ".join(f["claim"] for f in r3.get("facts", []))

    fabricated_markers = ["847", "Jean-Pierre Morel", "Pandemic Response Unit"]
    found_in_unsupported = any(m in unsupported_text for m in fabricated_markers)
    leaked_to_facts = any(m in facts_text for m in fabricated_markers)

    if found_in_unsupported and not leaked_to_facts:
        print("\n  [PASS] PASS: Fabricated claims correctly placed in unsupported_claims")
    elif leaked_to_facts:
        print("\n  [FAIL] FAIL: Fabricated claim LEAKED into facts --anti-hallucination violated!")
    else:
        print("\n  ~ WARN: Fabricated markers not found verbatim (check output manually)")

    input_urls_3 = {s["url"] for s in public_sources}
    violations_3 = assert_no_hallucinated_urls(r3, input_urls_3)
    all_url_violations.extend(violations_3)

    # ------------------------------------------------------------------
    # TEST 4: Gibberish sources --should not support any real claim
    # ------------------------------------------------------------------
    print("\n--- Test 4: Gibberish content + irrelevant sources ---")
    print(f"  Content: {GIBBERISH_CONTENT}")
    print(f"  Sources provided: {len(gibberish_sources)} (flight tracker, clothing store, etc.)")
    r4 = await run_verifier(GIBBERISH_CONTENT, gibberish_sources, "public")
    _print_result(r4)

    facts_count = len(r4.get("facts", []))
    if facts_count == 0:
        print("\n  [PASS] PASS: No facts extracted from gibberish --correct behavior")
    else:
        print(f"\n  [FAIL] FAIL: {facts_count} fact(s) extracted from gibberish content!")

    input_urls_4 = {s["url"] for s in gibberish_sources}
    violations_4 = assert_no_hallucinated_urls(r4, input_urls_4)
    all_url_violations.extend(violations_4)

    # ------------------------------------------------------------------
    # TEST 5: Refuted claim -- "Lyon is the capital of France"
    # ------------------------------------------------------------------
    print("\n--- Test 5: Refuted claim -- 'Lyon is the capital of France' ---")
    lyon_content = "Lyon is the capital of France and the largest city in the country."
    lyon_sources = [
        {
            "url": "https://en.wikipedia.org/wiki/France",
            "title": "France - Wikipedia",
            "snippet": "France, officially the French Republic, is a country located primarily in Western Europe. Its capital and largest city is Paris.",
            "published_date": None,
            "domain_reputation_hint": "high",
        },
        {
            "url": "https://en.wikipedia.org/wiki/Paris",
            "title": "Paris - Wikipedia",
            "snippet": "Paris is the capital and largest city of France. With an official estimated population of 2,102,650 residents in January 2023.",
            "published_date": None,
            "domain_reputation_hint": "high",
        },
    ]
    r5 = await run_verifier(lyon_content, lyon_sources, "public")
    _print_result(r5)

    refuted_claims = r5.get("refuted_claims", [])
    refuted_text = " ".join(r.get("claim", "") for r in refuted_claims)
    unsupported_text_5 = " ".join(r5.get("unsupported_claims", []))
    facts_text_5 = " ".join(f["claim"] for f in r5.get("facts", []))

    lyon_in_refuted = any(k in refuted_text.lower() for k in ("lyon", "capital"))
    lyon_in_unsupported = any(k in unsupported_text_5.lower() for k in ("lyon", "capital"))
    lyon_in_facts = any(k in facts_text_5.lower() for k in ("lyon is the capital",))

    if lyon_in_refuted:
        print("\n  [PASS] PASS: 'Lyon is the capital' correctly placed in refuted_claims")
    elif lyon_in_unsupported:
        print("\n  [FAIL] FAIL: 'Lyon is the capital' placed in unsupported_claims instead of refuted_claims")
    elif lyon_in_facts:
        print("\n  [FAIL] FAIL: 'Lyon is the capital' LEAKED into facts!")
    else:
        print("\n  ~ WARN: Lyon claim not found verbatim in any category (check output manually)")

    input_urls_5 = {s["url"] for s in lyon_sources}
    violations_5 = assert_no_hallucinated_urls(r5, input_urls_5)
    all_url_violations.extend(violations_5)

    # Check correct_info mentions Paris
    correct_info_text = " ".join(r.get("correct_info", "") for r in refuted_claims)
    if "paris" in correct_info_text.lower():
        print("  [PASS] PASS: correct_info correctly mentions Paris")
    else:
        print("  ~ WARN: correct_info doesn't mention Paris (check output manually)")

    # ------------------------------------------------------------------
    # TEST 6: URL hallucination assertion (aggregated across all tests)
    # ------------------------------------------------------------------
    print("\n--- Test 6: URL hallucination check (all tests combined) ---")
    if not all_url_violations:
        print("  [PASS] PASS: Every URL in output exists in the input source list")
    else:
        print(f"  [FAIL] FAIL: {len(all_url_violations)} hallucinated URL(s) detected:")
        for v in all_url_violations:
            print(f"    - {v}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("All tests completed. Review outputs above for correctness.")
    print("=" * 70)

    # Exit with error code if any critical check failed
    if all_url_violations or leaked_to_facts or lyon_in_facts:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
