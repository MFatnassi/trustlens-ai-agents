"""
Scorer / Final Writer Agent -- Section 3.4 of the project specification

Produces the final output adapted to the detected mode:

  PUBLIC MODE:  Trust score (0-100) + plain-language explanation with
                concrete examples from the Verifier's analysis.
  NEWSROOM MODE: Structured brief with sections (Summary, Reliable vs
                 questionable sources, Contradictions, Editorial angles).

SAFETY RULE: Every score is DERIVED from the Verifier Agent's actual data
using a documented formula -- never an arbitrary number. The LLM is only
used to generate the human-readable explanation/brief, not the score itself.

Output matches the Section 7 API contract:
  {
    "mode": "public" | "newsroom",
    "result": { ... },            # structure differs by mode
    "sources_used": [{"url", "title"}]
  }
"""

import asyncio
import json
import logging

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

logger = logging.getLogger("trustlens.scorer")


# ---------------------------------------------------------------------------
# Trust score formula (Public mode) -- deterministic, not LLM-generated
# ---------------------------------------------------------------------------
# The score is derived from the Verifier's output using this formula:
#
#   total_claims = facts + unsupported_claims + refuted_claims
#   base_score   = (facts / total_claims) * 100      if total_claims > 0
#                  0                                  if total_claims == 0
#
#   Adjustments:
#     - Each high-confidence fact adds +2 bonus (max +10)
#     - Each low-confidence fact subtracts -2 (max -10)
#     - Each contradiction subtracts -5 (max -15)
#     - Each unsupported claim subtracts -3 (max -15)
#     - Each refuted claim subtracts -10 (max -30)
#     - Opinions are neutral (they don't affect the score)
#
#   Hard caps (prevent inflated scores from tangential facts):
#     - If any refuted claims exist: cap at 15
#     - If unsupported claims + contradictions: cap at 25
#     - If any unsupported claims exist: cap at 50
#
#   Final score is clamped to [0, 100].
#
# Rationale:
#   - A piece of content with all claims backed by sources scores ~100.
#   - Content with many unsupported claims scores lower.
#   - Contradictions reduce trust because sources disagree.
#   - The formula is transparent and reproducible.
# ---------------------------------------------------------------------------

def compute_trust_score(verifier_output: dict) -> int:
    """Compute a deterministic trust score from the Verifier's output.

    Returns an integer between 0 and 100.

    Formula:
      total_claims = facts + unsupported_claims + refuted_claims  (opinions are neutral)
      base_score   = (facts / total_claims) * 100

      Adjustments:
        +2 per high-confidence fact (max +10)
        -2 per low-confidence fact (max -10)
        -5 per contradiction (max -15)
        -3 per unsupported claim (max -15)
        -10 per refuted claim (max -30)

      Hard caps:
        - If any refuted claims exist: cap at 15 (sources actively disprove claims)
        - If unsupported + contradictions: cap at 25
        - If any unsupported claims exist: cap at 50

      Clamped to [0, 100].
    """
    facts = verifier_output.get("facts", [])
    unsupported = verifier_output.get("unsupported_claims", [])
    refuted = verifier_output.get("refuted_claims", [])
    contradictions = verifier_output.get("contradictions", [])

    n_facts = len(facts)
    n_unsupported = len(unsupported)
    n_refuted = len(refuted)
    n_contradictions = len(contradictions)

    # Total verifiable claims (opinions are neutral)
    total_claims = n_facts + n_unsupported + n_refuted
    if total_claims == 0:
        return 0

    # Base score: proportion of claims that are verified
    base_score = (n_facts / total_claims) * 100

    # Confidence bonuses/penalties (capped)
    high_count = sum(1 for f in facts if f.get("confidence") == "high")
    low_count = sum(1 for f in facts if f.get("confidence") == "low")
    confidence_bonus = min(high_count * 2, 10) - min(low_count * 2, 10)

    # Contradiction penalty (capped at -15)
    contradiction_penalty = min(n_contradictions * 5, 15)

    # Unsupported claims penalty (capped at -15)
    unsupported_penalty = min(n_unsupported * 3, 15)

    # Refuted claims penalty (capped at -30)
    refuted_penalty = min(n_refuted * 10, 30)

    final_score = (base_score + confidence_bonus
                   - contradiction_penalty - unsupported_penalty
                   - refuted_penalty)

    # Hard caps (applied in order of severity, most severe first):
    # 1. Refuted claims = sources actively disprove content → cap at 15
    # 2. Unsupported + contradictions → cap at 25
    # 3. Any unsupported claims → cap at 50
    if n_refuted > 0:
        final_score = min(final_score, 15)
    elif n_unsupported > 0 and n_contradictions > 0:
        final_score = min(final_score, 25)
    elif n_unsupported > 0:
        final_score = min(final_score, 50)

    return max(0, min(100, int(round(final_score))))


def compute_input_verdict(verifier_output: dict) -> str:
    """Determine a clear verdict for the user's input claim.

    Returns one of:
      "true"       — all claims verified, no contradictions, no refuted claims
      "false"      — any claims are refuted by sources, OR unsupported AND contradicted
      "unverified" — claims unsupported, but no direct contradiction or refutation
      "mixed"      — some claims verified, some not
    """
    facts = verifier_output.get("facts", [])
    unsupported = verifier_output.get("unsupported_claims", [])
    refuted = verifier_output.get("refuted_claims", [])
    contradictions = verifier_output.get("contradictions", [])

    n_facts = len(facts)
    n_unsupported = len(unsupported)
    n_refuted = len(refuted)
    n_contradictions = len(contradictions)

    # Refuted claims = sources actively disprove content → always "false"
    if n_refuted > 0:
        return "false"
    if n_unsupported == 0 and n_contradictions == 0:
        return "true"
    elif n_unsupported > 0 and n_contradictions > 0:
        return "false"
    elif n_unsupported > 0 and n_facts == 0:
        return "unverified"
    elif n_unsupported > 0:
        return "mixed"
    else:
        return "mixed"


# ---------------------------------------------------------------------------
# LLM agent for generating the plain-language explanation (Public mode)
# ---------------------------------------------------------------------------

PUBLIC_EXPLANATION_INSTRUCTION = """\
You are the Final Writer for TrustLens, a content-verification system.

You receive:
  - An INPUT VERDICT: "true", "false", "unverified", or "mixed".
  - A TRUST SCORE (0-100).
  - The VERIFIER OUTPUT containing facts, opinions, unsupported_claims,
    refuted_claims, and contradictions.
  - The ORIGINAL CONTENT that was analyzed.

Your job is to write a CLEAR, VERDICT-FIRST EXPLANATION that a non-expert
can understand immediately. Structure it EXACTLY like this:

LINE 1 — VERDICT (bold, one sentence):
  - If verdict is "false":      "FALSE — This claim is contradicted by verified sources."
    If refuted_claims exist, mention what the sources actually say.
  - If verdict is "true":       "TRUE — This claim is supported by verified sources."
  - If verdict is "unverified": "UNVERIFIED — No sources could confirm or deny this claim."
  - If verdict is "mixed":      "MIXED — Some claims are verified, others are not."

LINE 2 — TRUST SCORE:
  State the score and what the number means:
  - 80-100: "Highly trustworthy"
  - 60-79:  "Moderately trustworthy"
  - 40-59:  "Low trustworthiness"
  - 20-39:  "Largely unverified"
  - 0-19:   "Insufficient verifiable information"

THEN — KEY EVIDENCE (2-3 bullet points):
  - Focus on the USER'S ORIGINAL CLAIM first. Was it supported,
    refuted, or left unverified? By which specific source?
  - If claims were REFUTED, explain what the sources actually say
    (use the correct_info from refuted_claims).
  - Then mention any unsupported claims or contradictions.
  - Cite sources with both URL and title.

THEN — OPINIONS (if any found).

IMPORTANT:
  - The VERDICT and the user's original claim must come FIRST. Do NOT
    bury the answer under tangential facts.
  - Do NOT invent or change the trust score or verdict.
  - Keep the tone neutral, informative, and accessible.
  - Write 150-300 words.
  - LANGUAGE RULE: Write in the SAME LANGUAGE as the ORIGINAL CONTENT.
    If the content is in French, write in French. If in Spanish, write
    in Spanish. Match the input language exactly.

Respond with ONLY the explanation text -- no JSON wrapping.
"""

# ---------------------------------------------------------------------------
# Model fallback chain — ordered by reasoning quality (best first)
# ---------------------------------------------------------------------------
# Same fallback strategy as the Verifier: cycle through models when one
# is quota-exhausted. The Scorer needs decent writing quality but is less
# sensitive to reasoning depth than the Verifier.
#
#   gemini-2.5-flash       — 20 RPD, strongest
#   gemini-2.5-flash-lite  — 20 RPD, lighter
#   gemini-3.1-flash-lite  — 500 RPD, last resort

SCORER_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
]

public_writer_agent = LlmAgent(
    name="public_writer",
    model=SCORER_MODELS[0],
    description="Generates plain-language trust explanations for Public mode.",
    instruction=PUBLIC_EXPLANATION_INSTRUCTION,
)


# ---------------------------------------------------------------------------
# LLM agent for generating the structured brief (Newsroom mode)
# ---------------------------------------------------------------------------

NEWSROOM_BRIEF_INSTRUCTION = """\
You are the Final Writer for TrustLens, producing a structured journalistic
brief for Newsroom mode.

You receive the VERIFIER OUTPUT containing facts, opinions,
unsupported_claims, refuted_claims, and contradictions gathered from
multiple sources.

Write a structured brief with EXACTLY these four sections:

## Summary
A 2-3 sentence overview of the topic based on the verified facts.

## Reliable vs Questionable Sources
- List sources that provided well-supported, consistent information
  (reliable).
- List sources that made claims not corroborated by others, or that
  contradicted mainstream reporting (questionable).
- For each source, include both URL and title.

## Identified Contradictions
- Describe each contradiction found between sources.
- If no contradictions were found, state "No contradictions identified
  among the sources analyzed."

## Suggested Editorial Angles
- Based on the analysis, suggest 2-3 angles a journalist could pursue.
- Focus on gaps in coverage, unresolved contradictions, or claims
  that need further investigation.

IMPORTANT:
  - Ground everything in the VERIFIER OUTPUT data -- do not add your
    own knowledge or speculation.
  - Cite sources with both URL and title (security requirement).
  - Keep the tone professional and journalistic.
  - LANGUAGE RULE: Write the brief in the SAME LANGUAGE as the user's
    original input. If the input was in French, write in French.
    If in Spanish, write in Spanish. Match the input language exactly.

Respond with ONLY the brief text (using the ## headers above) -- no JSON.
"""

newsroom_writer_agent = LlmAgent(
    name="newsroom_writer",
    model=SCORER_MODELS[0],
    description="Generates structured journalistic briefs for Newsroom mode.",
    instruction=NEWSROOM_BRIEF_INSTRUCTION,
)


# ---------------------------------------------------------------------------
# Helper: extract sources_used list (Section 7 API contract)
# ---------------------------------------------------------------------------

def _extract_sources_used(sources: list[dict]) -> list[dict]:
    """Extract the sources_used list for the API response.

    Returns [{"url": str, "title": str}] per Section 7.
    """
    return [
        {"url": s.get("url", ""), "title": s.get("title", "")}
        for s in sources
        if s.get("url")
    ]


# ---------------------------------------------------------------------------
# Helper: run an LLM agent and return its text response
# ---------------------------------------------------------------------------

async def _run_writer(agent: LlmAgent, prompt: str) -> str:
    """Run a writer agent with model fallback and return the text output.

    Tries each model in SCORER_MODELS. On quota exhaustion (429), moves
    to the next model immediately. On transient errors (503), also moves on.
    """
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    last_error = None
    for model in SCORER_MODELS:
        # Create a fresh agent with this model, same name/instruction
        fallback_agent = LlmAgent(
            name=agent.name,
            model=model,
            description=agent.description,
            instruction=agent.instruction,
        )
        try:
            runner = InMemoryRunner(agent=fallback_agent, app_name="trustlens_scorer")
            session = await runner.session_service.create_session(
                app_name="trustlens_scorer", user_id="scorer"
            )
            result_text = ""
            for event in runner.run(
                user_id="scorer", session_id=session.id, new_message=message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    result_text = event.content.parts[0].text
                    break

            if not result_text.strip():
                raise ValueError("Writer returned empty response")

            logger.info("Writer '%s' succeeded with model: %s", agent.name, model)
            return result_text

        except Exception as e:
            last_error = e
            error_msg = str(e)
            is_quota = any(k in error_msg for k in ("429", "RESOURCE_EXHAUSTED"))
            is_transient = any(k in error_msg for k in ("503", "UNAVAILABLE", "404", "NOT_FOUND", "empty response"))

            if is_quota:
                logger.warning("Writer '%s' model %s quota exhausted, trying next model...", agent.name, model)
                continue
            elif is_transient:
                logger.warning("Writer '%s' model %s transient error (%s), trying next model...", agent.name, model, error_msg[:80])
                continue
            else:
                raise

    raise last_error


# ---------------------------------------------------------------------------
# Main Scorer function
# ---------------------------------------------------------------------------

async def run_scorer(
    mode: str,
    content: str,
    verifier_output: dict,
    sources: list[dict],
) -> dict:
    """Execute the Scorer / Final Writer Agent.

    Produces the final API response matching Section 7:
      {"mode", "result", "sources_used"}

    Args:
        mode: "public" or "newsroom".
        content: The original user input text.
        verifier_output: Dict from the Verifier Agent (Section 3.3 schema).
        sources: List of source dicts from the Scout Agent (Section 3.2 schema).

    Returns:
        Dict matching Section 7 API contract.
    """
    sources_used = _extract_sources_used(sources)

    if mode == "public":
        return await _score_public(content, verifier_output, sources_used)
    else:
        return await _score_newsroom(content, verifier_output, sources_used)


async def _score_public(
    content: str,
    verifier_output: dict,
    sources_used: list[dict],
) -> dict:
    """Generate Public mode output: trust score + verdict + explanation."""

    # Step 1: Compute trust score and verdict deterministically
    trust_score = compute_trust_score(verifier_output)
    input_verdict = compute_input_verdict(verifier_output)

    # Step 2: Generate plain-language explanation via LLM
    prompt = (
        f"INPUT VERDICT: {input_verdict}\n"
        f"TRUST SCORE: {trust_score}/100\n\n"
        f"ORIGINAL CONTENT:\n{content}\n\n"
        f"VERIFIER OUTPUT:\n{json.dumps(verifier_output, indent=2)}"
    )
    explanation = await _run_writer(public_writer_agent, prompt)

    return {
        "mode": "public",
        "result": {
            "input_verdict": input_verdict,
            "trust_score": trust_score,
            "explanation": explanation,
        },
        "sources_used": sources_used,
    }


async def _score_newsroom(
    content: str,
    verifier_output: dict,
    sources_used: list[dict],
) -> dict:
    """Generate Newsroom mode output: structured brief."""

    prompt = (
        f"ORIGINAL INPUT:\n{content}\n\n"
        f"VERIFIER OUTPUT:\n{json.dumps(verifier_output, indent=2)}\n\n"
        f"SOURCES USED:\n{json.dumps(sources_used, indent=2)}"
    )
    brief = await _run_writer(newsroom_writer_agent, prompt)

    return {
        "mode": "newsroom",
        "result": {
            "brief": brief,
        },
        "sources_used": sources_used,
    }
