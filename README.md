# TrustLens

> An adaptive multi-agent system that fact-checks content and produces sourced, journalist-grade briefs — built for the **"AI Agents: Intensive Vibe Coding" Capstone** (Google × Kaggle), track **Agents for Good**.

TrustLens takes any free-text input and automatically decides what the user needs:

- **Public Mode** — you paste an article, a URL, or a claim → TrustLens breaks it into sourced facts / opinions / unverified claims and returns a deterministic **trust score (0–100)** with a plain-language, verdict-first explanation.
- **Newsroom Mode** — you type a topic or a monitoring query → TrustLens cross-references multiple sources and returns a structured **journalistic brief** (summary, reliable vs. questionable sources, contradictions, editorial angles).

One agentic backend, two audiences. A **Router Agent** analyzes the input and selects the mode.

---

## Table of Contents

- [Why agents](#why-agents)
- [Architecture](#architecture)
- [Safety guarantees](#safety-guarantees)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Running locally](#running-locally)
- [API contract](#api-contract)
- [Testing](#testing)
- [Deployment](#deployment)
- [How it was built](#how-it-was-built)
- [Roadmap](#roadmap)

---

## Why agents

Fact-checking is not a single LLM call. It is a pipeline of distinct reasoning steps — classify intent, search the open web, separate fact from opinion, detect contradictions, and score deterministically — each with different model and tooling needs. TrustLens models each step as a dedicated agent so that:

- the **search** step is grounded in a real tool (an MCP web-search server), not the model's memory;
- the **scoring** step is a documented deterministic formula, never an LLM-invented number;
- each agent stays small, testable, and independently swappable.

## Architecture

```
User input (free text)
        │
        ▼
┌────────────────────┐
│ Router Agent          │  Classifies the input:
│ (Gemini Flash Lite)   │  - "public"   → fact-check a single piece of content
└────────────────────┘  - "newsroom" → monitor a broad topic
        │
        ▼
┌────────────────────┐
│ Scout Agent           │  Runs targeted (public) or broad (newsroom) web
│ (→ Tavily MCP Server) │  searches. Collects real sources — never fabricates.
└────────────────────┘
        │
        ▼
┌────────────────────┐
│ Verifier Agent        │  Separates facts / opinions / unsupported claims,
│ (Gemini Flash)        │  flags refuted claims and cross-source contradictions.
└────────────────────┘
        │
        ▼
┌────────────────────┐
│ Scorer / Final Writer │  Public  → input_verdict + deterministic trust_score + explanation
│ (Gemini Flash)        │  Newsroom → structured journalistic brief
└────────────────────┘
        │
        ▼
   JSON response (mode-adapted, in the user's language)
```

See [`docs/architecture-diagram.png`](docs/architecture-diagram.png) for the full diagram.

### Agents

| Agent | Role | Model |
|---|---|---|
| **Router** ([`router_agent.py`](backend/agents/router_agent.py)) | Classifies input as `public` or `newsroom`, normalizes the query, detects language | `gemini-3.1-flash-lite` |
| **Scout** ([`scout_agent.py`](backend/agents/scout_agent.py)) | Collects sources via the Tavily MCP server (1 targeted search in public mode, multiple in newsroom mode) | `gemini-3.1-flash-lite` |
| **Verifier** ([`verifier_agent.py`](backend/agents/verifier_agent.py)) | Separates facts/opinions/unsupported/refuted claims, detects contradictions | `gemini-2.5-flash` (with fallback chain) |
| **Scorer** ([`scorer_agent.py`](backend/agents/scorer_agent.py)) | Produces the final verdict + trust score (public) or brief (newsroom) | `gemini-2.5-flash` (with fallback chain) |

The orchestrator that chains them lives in [`backend/orchestrator.py`](backend/orchestrator.py).

### Trust score (deterministic)

The trust score is **computed by code, never by the LLM**. The Scorer's LLM only writes the human-readable explanation. The formula:

- **Base** = (verified facts / total claims) × 100
- **Adjustments**: +2 per high-confidence fact (max +10), −2 per low (max −10), −5 per contradiction (max −15), −3 per unsupported claim (max −15)
- **Hard caps**: any unsupported claims → capped at 50; unsupported + contradictions → capped at 25; any refuted claims → capped at 15

## Safety guarantees

These are non-negotiable and enforced in code:

1. **Always cite sources** — every output includes the URL + title of each source used.
2. **Never hallucinate a source** — if the Scout Agent finds nothing, the system says so explicitly. The MCP client returns an empty list rather than inventing a result (see [`search_mcp_client.py`](backend/mcp_client/search_mcp_client.py)).
3. **No hardcoded secrets** — all keys are read from environment variables; `.env` is git-ignored, only `.env.example` is committed.
4. **Clear epistemic labels** — outputs always distinguish *verified fact*, *AI inference / opinion*, and *unverifiable*.

## Tech stack

| Component | Choice |
|---|---|
| Agent orchestration | **Google ADK** (multi-agent: Router, Scout, Verifier, Scorer) |
| LLM | **Gemini** (Flash Lite for Router/Scout, Flash for Verifier/Scorer) |
| Web search | **Tavily MCP Server** (real MCP client/server integration via `tavily-mcp`) |
| Backend API | **FastAPI** — single `/analyze` endpoint + `/health` |
| Frontend | **Next.js 16 + React 19 + Tailwind CSS 4** (single adaptive interface) |
| Assisted development | **Antigravity CLI** (vibe-coding workflow) |
| Deployment target | Backend → **Cloud Run**, Frontend → **Vercel** |

## Project structure

```
TrustLens/
├── README.md
├── .env.example                 # Env variables — NEVER commit real keys
├── backend/
│   ├── agents/
│   │   ├── router_agent.py
│   │   ├── scout_agent.py
│   │   ├── verifier_agent.py
│   │   └── scorer_agent.py
│   ├── mcp_client/
│   │   └── search_mcp_client.py # MCP client for the Tavily search server
│   ├── orchestrator.py          # Chains the 4 agents based on mode
│   ├── api.py                   # FastAPI /analyze + /health
│   ├── tests/                   # pytest suite + JSON fixtures
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Single input + adaptive result
│   │   └── components/
│   │       ├── PublicResultView.tsx
│   │       └── NewsroomResultView.tsx
│   └── package.json
└── docs/
    ├── architecture-diagram.png
    └── kaggle-writeup.md
```

## Setup

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (required: the Scout Agent spawns the Tavily MCP server via `npx`)
- A **Gemini API key** — free at [aistudio.google.com](https://aistudio.google.com/apikey)
- A **Tavily API key** — free at [app.tavily.com](https://app.tavily.com) (1,000 credits/month, no credit card)

### 1. Configure environment variables

Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

```dotenv
# .env (never commit this file)
GOOGLE_API_KEY=your-gemini-api-key-here
TAVILY_API_KEY=your-tavily-api-key-here
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Running locally

**Terminal 1 — backend** (from `backend/`, with the venv active):

```bash
uvicorn api:app --reload --port 8000
```

The API is now at `http://127.0.0.1:8000` (health check: `GET /health`).

**Terminal 2 — frontend** (from `frontend/`):

```bash
npm run dev
```

Open `http://localhost:3000`. The frontend talks to the backend at `http://127.0.0.1:8000` by default; override with `NEXT_PUBLIC_API_URL` if needed.

Quick API smoke test:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"input": "Is it true that the new H5N1 vaccine causes infertility?"}'
```

## API contract

### `POST /analyze`

Request:

```json
{ "input": "string (text, URL, or monitoring topic)" }
```

Response — **Public mode**:

```json
{
  "mode": "public",
  "result": {
    "input_verdict": "true | false | unverified | mixed",
    "trust_score": 0,
    "explanation": "verdict-first plain-language text, in the input language"
  },
  "sources_used": [{ "url": "string", "title": "string" }],
  "detected_language": "en"
}
```

Response — **Newsroom mode**:

```json
{
  "mode": "newsroom",
  "result": {
    "brief": "structured journalistic brief with ## sections, in the input language"
  },
  "sources_used": [{ "url": "string", "title": "string" }],
  "detected_language": "en"
}
```

Errors:

- `400` — empty input or input exceeding 10,000 characters
- `504` — pipeline timed out (120 s limit)
- `500` — internal server error (logged server-side)

### `GET /health`

```json
{ "status": "ok" }
```

## Testing

The backend ships with a pytest suite covering each agent, the orchestrator end-to-end, and the API contract (with JSON fixtures so tests run without burning API quota).

```bash
cd backend
pytest
```

## Deployment

> Not required to be live for judging, but the process is documented here.

### Backend → Google Cloud Run

1. Containerize the FastAPI app (a `Dockerfile` running `uvicorn api:app --host 0.0.0.0 --port 8080`).
2. Build and deploy:
   ```bash
   gcloud run deploy trustlens-api \
     --source backend \
     --region europe-west1 \
     --allow-unauthenticated \
     --set-env-vars GOOGLE_API_KEY=...,TAVILY_API_KEY=...
   ```
3. Note the Cloud Run image must include **Node.js** so the Scout Agent can spawn the Tavily MCP server via `npx`.
4. Restrict CORS in [`api.py`](backend/api.py) to your Vercel frontend domain before going public.

### Frontend → Vercel

1. Import the `frontend/` directory as a Vercel project.
2. Set the environment variable `NEXT_PUBLIC_API_URL` to your Cloud Run URL.
3. Deploy — Vercel auto-detects Next.js.

## How it was built

TrustLens was developed using a **vibe-coding** workflow with the **Antigravity CLI** as the assisted-development environment, iterating on agent prompts and the deterministic scoring logic against real cases (one suspicious health claim, one live monitoring topic). Gemini was used both as the inference engine and as an iterative prompt-refinement tool.

This project demonstrates **6** of the course's concepts (3 required):

1. Multi-agent system (Google ADK)
2. MCP Server (Tavily web search)
3. Antigravity (development workflow)
4. Security features (anti-hallucination, mandatory source citation, deterministic scoring)
5. Deployability (Cloud Run + Vercel)
6. Agent skills (Antigravity CLI)

## Roadmap

Planned extensions, **not** in scope for the current capstone submission:

- **Image verification** — reverse image search to detect images reused in misleading contexts (Gemini multimodal + a reverse-image-search MCP server).
- **Deepfake / AI-generation detection** — specialized detection models.
- **Batch analysis** — submit multiple articles or RSS feeds for continuous newsroom monitoring.

---

*Built for the Google × Kaggle "AI Agents: Intensive Vibe Coding" Capstone — track Agents for Good.*
