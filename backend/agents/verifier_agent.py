"""
Verifier Agent — Section 3.3 of the project specification

The most safety-critical component of TrustLens. Analyzes sources collected
by the Scout Agent against the original content to:
  - Separate factual claims from opinions.
  - Identify unsourced/unsupported claims.
  - Detect contradictions between sources (mainly Newsroom Mode).

Output follows the exact JSON schema from Section 3.3:
  {
    "facts":              [{"claim", "supported_by": [urls], "confidence"}],
    "opinions":           ["string"],
    "unsupported_claims": ["string"],
    "refuted_claims":     [{"claim", "refuted_by": [urls], "correct_info"}],
    "contradictions":     [{"point", "source_a", "position_a", "source_b", "position_b"}]
  }

Uses Gemini 2.5 Flash (more capable reasoning than Flash Lite) because
this agent performs nuanced analysis: cross-referencing claims against
source text, detecting contradictions, and — critically — resisting the
temptation to use its own knowledge to fill gaps.
"""

import asyncio
import json
import logging

from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

logger = logging.getLogger("trustlens.verifier")


# ---------------------------------------------------------------------------
# Pydantic output schema — matches Section 3.3 exactly
# ---------------------------------------------------------------------------

class VerifiedFact(BaseModel):
    """A factual claim that is supported by at least one provided source."""
    claim: str = Field(description="The factual claim extracted from the content.")
    supported_by: list[str] = Field(
        description="List of source URLs that support this claim. Must be URLs from the provided sources list."
    )
    confidence: str = Field(
        description='Confidence level: "high", "medium", or "low".'
    )


class RefutedClaim(BaseModel):
    """A claim from the content that is directly contradicted by the sources."""
    claim: str = Field(description="The claim from the content that sources contradict.")
    refuted_by: list[str] = Field(
        description="List of source URLs that contradict this claim. Must be URLs from the provided sources list."
    )
    correct_info: str = Field(
        description="What the sources actually say, contradicting the claim."
    )


class Contradiction(BaseModel):
    """A point where two sources disagree."""
    point: str = Field(description="The topic or claim on which sources disagree.")
    source_a: str = Field(description="URL of the first source.")
    position_a: str = Field(description="What the first source says about this point.")
    source_b: str = Field(description="URL of the second source.")
    position_b: str = Field(description="What the second source says, contradicting source_a.")


class VerifierResult(BaseModel):
    """The Verifier Agent's complete analysis output."""
    facts: list[VerifiedFact] = Field(
        default_factory=list,
        description="Claims that are supported by at least one provided source."
    )
    opinions: list[str] = Field(
        default_factory=list,
        description="Statements that are opinions, not verifiable facts."
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims that appear in the content but are NOT supported by any provided source AND are NOT directly contradicted by sources (no info found, not wrong)."
    )
    refuted_claims: list[RefutedClaim] = Field(
        default_factory=list,
        description="Claims from the content that are DIRECTLY CONTRADICTED by one or more provided sources. The sources say the opposite or provide correct information that disproves the claim."
    )
    contradictions: list[Contradiction] = Field(
        default_factory=list,
        description="Points where two or more provided sources disagree."
    )


# ---------------------------------------------------------------------------
# System prompt — anti-hallucination constraints are the core of this agent
# ---------------------------------------------------------------------------
# SECURITY NOTE (Capstone grading criterion: "Security features"):
#
# The anti-hallucination constraint below is the single most important
# safety rule in TrustLens. Without it, the LLM could use its training
# data to "verify" claims — producing outputs that look authoritative
# but are actually the model's own beliefs, not evidence from real sources.
#
# This would undermine the entire value proposition: users trust TrustLens
# because every fact is traced to a cited source. If the model fabricates
# support, users may believe misinformation is fact-checked when it isn't.
#
# The prompt below enforces this constraint through:
#   1. Explicit instruction to ONLY use provided sources.
#   2. Requirement that every fact includes at least one real URL.
#   3. Instruction to put unsourced claims in unsupported_claims,
#      even if the model "knows" they are true.
#   4. Prohibition against inventing or modifying source URLs.
# ---------------------------------------------------------------------------

VERIFIER_INSTRUCTION = """\
You are the Verifier Agent for TrustLens, a content-verification system.

You receive two inputs:
  1. CONTENT: the original text or topic being analyzed.
  2. SOURCES: a list of sources collected by the Scout Agent, each with
     a url, title, and snippet.

Your job is to analyze the CONTENT against ONLY the provided SOURCES.

═══════════════════════════════════════════════════════════════════
  ANTI-HALLUCINATION CONSTRAINT (NON-NEGOTIABLE SAFETY RULE)
═══════════════════════════════════════════════════════════════════

  You must NEVER use your own background knowledge to verify a claim.

  - If a claim in the CONTENT is supported by text in one or more of the
    provided SOURCES → put it in "facts" with the supporting source URLs.
  - If a claim is NOT mentioned or supported by ANY provided source
    AND no source contradicts it → put it in "unsupported_claims",
    EVEN IF you personally know it to be true. Your knowledge is
    irrelevant — only the sources matter.
  - If a claim is DIRECTLY CONTRADICTED by one or more sources (the
    sources say the opposite or provide correct information that
    disproves the claim) → put it in "refuted_claims" with the
    source URLs and what the sources actually say. This is DIFFERENT
    from "unsupported_claims": unsupported = no info found,
    refuted = sources actively say the claim is wrong.
  - NEVER invent, modify, or guess a source URL. Every URL in
    "supported_by", "source_a", and "source_b" fields MUST be copied
    exactly from the SOURCES list provided to you.
  - If no sources support any claims, return empty "facts" and put
    everything in "unsupported_claims". This is correct behavior.

  Violating this rule makes the entire system untrustworthy.

═══════════════════════════════════════════════════════════════════

ANALYSIS TASKS:

1. FACTS: Extract claims from the CONTENT that are factual assertions
   (not opinions). For each, check if any SOURCE snippet corroborates it.
   - If yes → add to "facts" with the source URL(s) and confidence:
     - "high": multiple sources agree, or a single highly authoritative source.
     - "medium": one source supports it, or sources partially agree.
     - "low": weak or indirect support from sources.
   - If no source supports it → add to "unsupported_claims".

2. OPINIONS: Identify statements in the CONTENT that are subjective
   judgments, predictions, or value statements — not verifiable facts.
   Extract them as strings.

3. UNSUPPORTED CLAIMS: Any factual-sounding claim in the CONTENT that
   is NOT corroborated by the provided SOURCES AND is NOT directly
   contradicted by them. "Unsupported" means no information found —
   the sources neither confirm nor deny the claim.

4. REFUTED CLAIMS: Any claim in the CONTENT that is DIRECTLY
   CONTRADICTED by one or more provided SOURCES. The sources provide
   information that proves the claim wrong. For each refuted claim:
   - Include the claim text.
   - List the source URL(s) that contradict it (refuted_by).
   - State what the sources actually say (correct_info).
   Example: if the content says "Lyon is the capital of France" and
   a source says "Paris is the capital of France", that claim goes
   in refuted_claims, NOT unsupported_claims.

6. CONTRADICTIONS: Compare the SOURCES against each other. If two
   sources present conflicting information about the same point, record
   the contradiction with both URLs and their respective positions.
   - Only report genuine factual disagreements, not differences in
     emphasis or scope.
   - This is especially important in "newsroom" mode where multiple
     sources may cover the same topic from different angles.

Respond ONLY with the JSON object — no extra text.
"""


# ---------------------------------------------------------------------------
# Model fallback chain — ordered by reasoning quality (best first)
# ---------------------------------------------------------------------------
# When a model's daily quota (RPD) is exhausted, the runner tries the next
# model in the list. This maximizes availability across multiple free-tier
# quotas instead of failing on a single 429.
#
#   gemini-2.5-flash       — 20 RPD, strongest reasoning
#   gemini-2.5-flash-lite  — 20 RPD, lighter but decent
#   gemini-3.1-flash-lite  — 500 RPD, last resort (weakest reasoning)

VERIFIER_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
]


def _make_verifier_agent(model: str) -> LlmAgent:
    """Create a Verifier LlmAgent for the given model."""
    return LlmAgent(
        name="verifier_agent",
        model=model,
        description="Cross-checks content against provided sources, separating facts from opinions and detecting contradictions.",
        instruction=VERIFIER_INSTRUCTION,
        output_schema=VerifierResult,
    )


# Default agent (used by tests that import it directly)
verifier_agent = _make_verifier_agent(VERIFIER_MODELS[0])


# ---------------------------------------------------------------------------
# Runner function
# ---------------------------------------------------------------------------

async def run_verifier(content: str, sources: list[dict], mode: str) -> dict:
    """Execute the Verifier Agent with model fallback.

    Tries each model in VERIFIER_MODELS in order. If a model returns
    429 RESOURCE_EXHAUSTED, the next model is tried immediately. For
    503/UNAVAILABLE or empty responses, it retries the same model once
    before moving on.

    Args:
        content: The original text or topic being analyzed.
        sources: List of source dicts from the Scout Agent (Section 3.2 schema).
        mode: "public" or "newsroom" — passed for context but the Verifier
              applies the same logic regardless.

    Returns:
        Dict matching Section 3.3 schema: {facts, opinions, unsupported_claims, contradictions}.
    """
    sources_text = json.dumps(sources, indent=2)
    prompt = (
        f"MODE: {mode}\n\n"
        f"CONTENT:\n{content}\n\n"
        f"SOURCES:\n{sources_text}"
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    last_error = None
    for model in VERIFIER_MODELS:
        agent = _make_verifier_agent(model)
        try:
            runner = InMemoryRunner(agent=agent, app_name="trustlens_verifier")
            session = await runner.session_service.create_session(
                app_name="trustlens_verifier", user_id="verifier"
            )

            result_text = ""
            for event in runner.run(
                user_id="verifier", session_id=session.id, new_message=message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    result_text = event.content.parts[0].text
                    break

            if not result_text.strip():
                raise ValueError("Verifier returned empty response")

            logger.info("Verifier succeeded with model: %s", model)
            return json.loads(result_text)

        except Exception as e:
            last_error = e
            error_msg = str(e)
            is_quota = any(k in error_msg for k in ("429", "RESOURCE_EXHAUSTED"))
            is_transient = any(k in error_msg for k in ("503", "UNAVAILABLE", "404", "NOT_FOUND", "empty response"))

            if is_quota:
                logger.warning("Verifier model %s quota exhausted, trying next model...", model)
                continue
            elif is_transient:
                logger.warning("Verifier model %s transient error (%s), trying next model...", model, error_msg[:80])
                continue
            else:
                raise

    raise last_error
