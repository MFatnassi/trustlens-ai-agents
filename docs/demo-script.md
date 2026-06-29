# TrustLens — Demo Video Script (≤ 5 minutes)

> Capstone: "AI Agents: Intensive Vibe Coding" (Google × Kaggle) — track **Agents for Good**.
> Required structure: **problem → why agents → architecture → live demo → how it was built** (must mention **Antigravity CLI**).
>
> **Language note:** narration is written in English (UI is English, judges are international). You can deliver it in French if you prefer — the timing stays the same.
>
> **Total target: ~4 min 40 s** — leaving margin under the 5-minute hard limit.
>
> **Before recording — checklist:**
> - [ ] Backend running: `uvicorn api:app --reload --port 8000`
> - [ ] Frontend running: `npm run dev` → `http://localhost:3000`
> - [ ] Do **one warm-up run of each example** before recording (first call spins up the Tavily MCP `npx` server and Gemini — avoids a slow first response on camera).
> - [ ] `docs/architecture-diagram.png` open in a tab/window for the architecture section.
> - [ ] Screen recorder ready (OBS / Loom / built-in). Record at 1080p.

---

## Section 1 — The Problem (0:00 – 0:40) · ~40 s

**On screen:** Your face (webcam) OR the TrustLens landing page, static.

**Voiceover:**
> "Every day we read claims online — in articles, on social media, in group chats. The hard part isn't reading them; it's knowing what's actually *verified*, what's just *opinion*, and what's simply *made up*.
>
> Most AI tools make this worse: ask a chatbot 'is this true?' and it answers confidently — sometimes citing sources that don't even exist.
>
> TrustLens is built to do the opposite: it never invents a source, it always shows its evidence, and it scores trust with a transparent formula — not a number the AI made up."

---

## Section 2 — Why Agents (0:40 – 1:15) · ~35 s

**On screen:** The architecture diagram (`docs/architecture-diagram.png`), or a simple bullet build-up.

**Voiceover:**
> "Fact-checking isn't a single AI call — it's a pipeline of different jobs. You have to understand the request, search the live web, separate fact from opinion, spot contradictions, and then score the result.
>
> So TrustLens uses **four specialized agents**, each doing one job well, orchestrated with **Google's Agent Development Kit**. This keeps every step grounded, testable, and honest — the search is done by a real tool, and the score is computed by code, never guessed by the model."

---

## Section 3 — Architecture (1:15 – 2:15) · ~60 s

**On screen:** The architecture diagram. Point to each agent as you name it (cursor or highlight).

**Voiceover:**
> "Here's how it works. The input is free text, and a **Router Agent** classifies it into one of two modes.
>
> If it's a single claim or article, that's **Public Mode**. If it's a broad topic to monitor, that's **Newsroom Mode**.
>
> Next, the **Scout Agent** searches the open web — through a real **MCP server**, the Tavily search server. Crucially, if it finds nothing, it says so. It never fabricates a source.
>
> The **Verifier Agent** then takes those sources and separates verified facts from opinions and unsupported claims, and flags anything the sources directly contradict.
>
> Finally, the **Scorer Agent** produces the output: in Public Mode, a verdict and a deterministic trust score from 0 to 100; in Newsroom Mode, a structured journalistic brief. The AI only writes the explanation — the number itself comes from a documented formula."

---

## Section 4 — Live Demo (2:15 – 4:05) · ~110 s

> This is the core. Switch to the browser at `http://localhost:3000`. Speak while it runs; the pipeline takes ~30 s, so keep narrating during the loading animation (the loading steps on screen actually name each agent — point that out).

### Demo 4A — Public Mode (fact-check) · ~55 s

**Action:** Paste this exact input into the field and click **Start Pipeline Analysis**:

```
Humans only use 10 percent of their brains.
```

**Voiceover (while loading):**
> "Let's start with something everyone has heard — the myth that we only use 10 percent of our brains. Watch the loading steps: you can literally see each agent run — the Router classifies it, the Scout searches the web, the Verifier cross-checks, and the Scorer computes the result."

**Action:** When the result appears, point to: the **verdict**, the **trust score**, and the **sources list**.

**Voiceover (on result):**
> "And here's the verdict — false, with a low trust score, because the sources clearly refute it. Every source it used is listed right here, with a clickable link. No invented evidence. That's the whole point."

### Demo 4B — Newsroom Mode (monitoring) · ~55 s

**Action:** Clear the field and paste this exact input:

```
the effects of drinking coffee on health
```

**Voiceover (while loading):**
> "Now a completely different need — researching a broad, everyday topic where sources genuinely disagree. Same single input box, but the Router detects this is a topic, not a single claim, and switches to Newsroom Mode."

**Action:** When the brief appears, scroll slowly through the sections — pause on the **contradictions** section.

**Voiceover (on result):**
> "Instead of a score, we get a structured brief: a summary, which sources are reliable versus questionable, and — most useful here — the contradictions between them, since some studies call coffee healthy and others raise concerns. Plus suggested angles to cover. Every claim stays tied to its source."

---

## Section 5 — How It Was Built (4:05 – 4:40) · ~35 s

**On screen:** Quick montage — the code (the `agents/` folder), then back to the app.

**Voiceover:**
> "Under the hood: **Google ADK** orchestrates the four agents, **Gemini** powers the reasoning, the **Tavily MCP server** handles live search, **FastAPI** serves the backend, and a **Next.js** front end adapts to each mode.
>
> The whole thing was built with a vibe-coding workflow using the **Antigravity CLI** — iterating on agent prompts and the scoring logic against real cases.
>
> TrustLens: verifiable, sourced, and honest by design. Thanks for watching."

---

## On-screen text / lower-thirds (optional but recommended)

| Time | Caption to display |
|---|---|
| 0:00 | TrustLens — AI that fact-checks honestly |
| 1:15 | 4 agents · Google ADK |
| 1:40 | Real MCP search (Tavily) — never fabricates sources |
| 2:15 | LIVE DEMO |
| 4:05 | Built with Antigravity CLI |

## Backup examples (if a demo input returns a weak result on the day)

Simple, universally understood inputs that produce clean results:

- **Public (alternative claims):**
  - `The Great Wall of China is the only man-made object visible from space with the naked eye.` (myth → false)
  - `Lightning never strikes the same place twice.` (myth → false)
  - `Drinking water helps keep the body hydrated.` (obvious → true, good to show a high score too)
- **Newsroom (alternative topics):**
  - `the impact of social media on teenagers' mental health`
  - `are electric cars better for the environment than gasoline cars`

> Tip: whatever you record, do a dry run of the exact inputs right before recording so you know what the result looks like and can narrate confidently.
