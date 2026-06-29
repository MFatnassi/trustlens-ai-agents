"""
Router Agent (Classifier Agent) — Section 3.1 of the project specification

Analyzes user input and classifies it into one of two modes:
  - "public"   : the input is a long text, article, or URL to fact-check.
  - "newsroom" : the input is a short topic, keywords, or monitoring request.

Uses Google ADK with Gemini Flash (fast, low-cost) for classification.
Output follows the exact JSON schema from the project spec:
  { "mode": "public"|"newsroom", "normalized_query": str, "confidence": float }
"""

from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent

# ---------------------------------------------------------------------------
# Structured output schema — enforces the JSON contract from Section 3.1
# ---------------------------------------------------------------------------

class RouterResult(BaseModel):
    """The Router Agent's classification output."""
    mode: str = Field(
        description='Either "public" or "newsroom".'
    )
    normalized_query: str = Field(
        description="A short, normalized version of the user's input suitable for downstream agents."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0 for the classification."
    )
    detected_language: str = Field(
        description='ISO 639-1 language code of the input (e.g. "en", "fr", "es", "ar").'
    )


# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------
# The prompt encodes the decision logic from Section 3.1:
#   - Long text / article body / URL / single piece of content → "public"
#   - Short query, topic, keywords, monitoring request     → "newsroom"
# We ask the model to also produce a normalized_query (a concise restatement
# of the user's intent) and a confidence score so downstream agents know how
# certain the classification is.
# ---------------------------------------------------------------------------

ROUTER_INSTRUCTION = """\
You are the Router Agent for TrustLens, a content-verification system.

Your ONLY job is to classify the user's input into one of two modes:

MODE "public"
  The user has provided a SPECIFIC piece of content to fact-check.
  Indicators:
    - A long block of text (article excerpt, social-media post, claim).
    - A URL pointing to an article or page.
    - A single statement or quote that the user wants verified.

MODE "newsroom"
  The user is asking about a BROAD TOPIC for journalistic monitoring.
  Indicators:
    - A short query with keywords (e.g. "election fraud claims 2026").
    - A request to monitor or survey a subject across multiple sources.
    - No specific article or URL — just a topic to investigate.

DECISION RULES (apply in order):
  1. If the input contains a URL → "public".
  2. If the input is longer than ~80 words of prose → "public".
  3. If the input is a short phrase, set of keywords, or a question
     asking to survey/monitor a topic → "newsroom".
  4. When in doubt, default to "public" (safer: fact-checking a single
     input is a subset of the newsroom workflow).

For `normalized_query`, produce a concise restatement of the user's
intent (max ~15 words). Strip filler words but keep the core meaning.

For `confidence`, output a float between 0.0 and 1.0 reflecting how
certain you are about the mode classification.

For `detected_language`, output the ISO 639-1 code of the input language
(e.g. "en" for English, "fr" for French, "es" for Spanish, "ar" for Arabic).

Respond ONLY with the JSON object — no extra text.
"""

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------
# We use LlmAgent with output_schema so ADK constrains the model to return
# valid JSON matching RouterResult. Model is Gemini 2.0 Flash — fast and
# inexpensive, appropriate for a lightweight classification task.
# ---------------------------------------------------------------------------

router_agent = LlmAgent(
    name="router_agent",
    model="gemini-3.1-flash-lite",
    description="Classifies user input as 'public' (fact-check) or 'newsroom' (topic monitoring).",
    instruction=ROUTER_INSTRUCTION,
    output_schema=RouterResult,
)
