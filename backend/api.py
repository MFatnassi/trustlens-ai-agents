"""
FastAPI application -- exposes the /analyze endpoint.

Section 7 of the project specification defines the API contract:
  POST /analyze
  Request:  { "input": "string" }
  Response: { "mode": "public"|"newsroom", "result": {...}, "sources_used": [...] }
"""

import asyncio
import logging
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from orchestrator import analyze

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trustlens.api")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum allowed input length in characters.
# 10,000 chars covers any reasonable article or topic query.
# Longer inputs would bloat the LLM context and slow the pipeline.
MAX_INPUT_LENGTH = 10_000

# Pipeline timeout in seconds.
# The e2e pipeline takes ~30s on average. 120s gives ample margin
# for slow Tavily responses or model latency spikes.
PIPELINE_TIMEOUT_SECONDS = 120

# CORS origins allowed for local frontend development.
# For production, restrict this to the actual frontend domain.
# See README for production CORS configuration.
import os

CORS_ORIGINS = [
    "http://localhost:3000",      # Next.js default dev port
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Allow overriding or extending CORS origins via environment variable in production
env_cors = os.environ.get("CORS_ORIGINS")
if env_cors:
    if env_cors.strip() == "*":
        CORS_ORIGINS = ["*"]
    else:
        CORS_ORIGINS.extend([origin.strip() for origin in env_cors.split(",") if origin.strip()])

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="TrustLens API",
    description="AI-powered content verification and trust scoring.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / Response models (Section 7 contract)
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    input: str = Field(
        ...,
        description="Text, URL, or monitoring topic to analyze.",
    )


class SourceUsed(BaseModel):
    url: str
    title: str


class AnalyzeResponse(BaseModel):
    mode: str
    result: dict
    sources_used: list[SourceUsed]
    detected_language: str = "en"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(request: AnalyzeRequest):
    """Analyze content for trustworthiness (Section 7 API contract).

    Chains all four agents: Router -> Scout -> Verifier -> Scorer.
    """
    # --- Input validation ---
    user_input = request.input.strip()

    if not user_input:
        raise HTTPException(
            status_code=400,
            detail="Input must not be empty.",
        )

    if len(user_input) > MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input too long ({len(user_input)} chars). Maximum is {MAX_INPUT_LENGTH} characters.",
        )

    # --- Run pipeline with timeout ---
    try:
        result = await asyncio.wait_for(
            analyze(user_input),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
        return result

    except asyncio.TimeoutError:
        logger.error("Pipeline timed out after %ds for input: %.100s...", PIPELINE_TIMEOUT_SECONDS, user_input)
        raise HTTPException(
            status_code=504,
            detail=f"Analysis timed out after {PIPELINE_TIMEOUT_SECONDS} seconds. Please try a shorter input or try again later.",
        )

    except HTTPException:
        raise

    except Exception:
        logger.error("Pipeline error for input: %.100s...\n%s", user_input, traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Internal server error during analysis. The error has been logged.",
        )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
