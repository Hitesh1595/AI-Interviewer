# AI Interviewer — Design Specification

**Date:** 2026-07-04
**Status:** Approved

## 1. Overview

An AI-powered interviewer that ingests a candidate's profile (GitHub, LinkedIn,
resume), conducts a time-boxed conversational interview calibrated to a target
seniority level, and produces a structured evaluation: a written summary, a
rating out of 10, and a **move-forward / do-not-move-forward** recommendation.

- **Backend:** FastAPI (Python 3.12), Google Gemini via `google-genai`,
  SQLModel + SQLite, WebSockets, `pypdf`, `httpx`.
- **Frontend:** React + Vite + TypeScript + Tailwind CSS.
- **Voice:** Browser-native Web Speech API (free STT + TTS). No paid services.
- **Orchestration:** Docker Compose (dev). Production build serves the compiled
  frontend as static files from FastAPI.

## 2. Goals & Non-Goals

**Goals**
- Aggregate candidate context from GitHub (public API), LinkedIn (pasted text or
  PDF export), and a PDF resume.
- Master settings: interview duration, interviewer level, candidate seniority
  (intern / junior / senior), focus areas.
- Live conversational interview (text-first, optional free voice).
- Deterministic, time-driven interview flow.
- Structured final evaluation with summary, `/10` score, and hire decision.
- Demonstrate clean engineering design patterns.

**Non-Goals (YAGNI)**
- No LinkedIn scraping (against ToS, fragile). Paste/PDF only.
- No paid voice (Deepgram). Browser Web Speech only.
- No auth / multi-tenant / user accounts in the scaffold.
- No live coding editor / IDE integration.

## 3. Architecture

Layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React + Vite)                                  │
│  Setup page · Interview page (WS + Web Speech) · Result   │
└───────────────┬───────────────────────────────┬──────────┘
        REST (setup, result)             WebSocket (live interview)
┌───────────────▼───────────────────────────────▼──────────┐
│  API layer (FastAPI)                                      │
│  sessions.py (REST) · interview_ws.py (WebSocket)         │
├───────────────────────────────────────────────────────────┤
│  Service layer                                            │
│  ProfileService · InterviewEngine · EvaluationService     │
│  LLMProvider (Gemini) · PromptBuilder                     │
├───────────────────────────────────────────────────────────┤
│  Domain layer                                             │
│  InterviewStateMachine · Strategies · Schemas · Enums     │
├───────────────────────────────────────────────────────────┤
│  Persistence layer                                        │
│  SessionRepository → SQLModel → SQLite                    │
└───────────────────────────────────────────────────────────┘
```

## 4. Design Patterns

| Pattern | Location | Responsibility |
|---|---|---|
| **Strategy** | `domain/strategies.py` | Per-seniority + interviewer-level behavior: question difficulty, rubric weights, tone, question count. |
| **Adapter** | `services/profile/{github,linkedin,resume}.py` | Normalize each source into a common `ProfileFragment`. |
| **Factory** | `services/llm/factory.py`, `services/profile/aggregator.py` | Construct the LLM provider and the set of active profile adapters. |
| **Builder** | `services/interview/prompt_builder.py` | Compose the system prompt from settings + `CandidateContext` + strategy. |
| **State Machine** | `domain/state_machine.py` | Drive `GREETING → QUESTIONING → FOLLOW_UP → WRAP_UP → EVALUATION → COMPLETE`. |
| **Repository** | `repository/session_repo.py` | Persist/retrieve sessions; hide SQLite behind an interface. |
| **Observer / streaming** | `api/interview_ws.py` | Push streamed tokens and state events to the client. |
| **Dependency Injection** | `api/deps.py` | Provide services to routes; trivially mockable in tests. |

## 5. Domain Model

### Enums
- `Seniority`: `INTERN | JUNIOR | SENIOR`
- `InterviewerLevel`: `SUPPORTIVE | BALANCED | RIGOROUS`
- `InterviewState`: `GREETING | QUESTIONING | FOLLOW_UP | WRAP_UP | EVALUATION | COMPLETE`
- `Recommendation`: `STRONG_NO | NO | YES | STRONG_YES`

### Key schemas (Pydantic)
- `InterviewConfig`: `role_title` (**required** — the position being interviewed
  for), `seniority`, `interviewer_level`, `duration_minutes`,
  `focus_areas: list[str]`.
- `ProjectSignal`: `name`, `description`, `tech: list[str]`, `url`, `source`.
- `ProfileFragment`: `source`, `summary`, `signals: dict`, `raw_excerpt`.
- `CandidateContext`: aggregated fragments + derived `tech_stack: list[str]`,
  `projects: list[ProjectSignal]`, `highlights: list[str]`,
  `available_sources: list[str]`.
- `Turn`: `role (interviewer|candidate)`, `content`, `ts`.
- `Evaluation`: `dimension_scores: dict[str,float]`, `overall_score: float`,
  `strengths`, `weaknesses`, `summary`, `recommendation`, `move_forward: bool`.

### Input & tailoring rules (R14–R16)
- **Any subset of inputs works.** GitHub, LinkedIn, and resume are each optional,
  but **at least one** must be provided (validated at `POST /api/sessions`).
  Adapters run independently; a failed/blocked source is skipped and recorded in
  `available_sources`.
- **Project / stack / technology specificity (R15).** Adapters extract structured
  signals, not just prose:
  - *GitHub* → top languages (by bytes), notable repos (name, description, topics,
    primary language, stars) → merged into `tech_stack` + `projects`.
  - *Resume* → skills/technologies section, listed projects, years of experience.
  - *LinkedIn* → headline, roles, companies.
  `PromptBuilder` injects `tech_stack` + `projects` and instructs the interviewer
  to ground questions in the candidate's **actual** work and named technologies,
  and to never invent facts about sources that weren't provided.
- **Position specificity (R16).** `role_title` + `focus_areas` steer question
  selection; the rubric's *Experience relevance* dimension scores how well the
  candidate's real stack/projects fit the target role and seniority.

## 6. Interview Flow

1. **Setup** — `POST /api/sessions` (multipart): GitHub URL, LinkedIn text or PDF,
   resume PDF, `InterviewConfig`. `ProfileService` runs each adapter (failures are
   isolated — a missing/blocked source degrades gracefully), aggregates into
   `CandidateContext`. Session persisted with `state=GREETING`.
2. **Interview** — client opens `ws /api/ws/interview/{id}`. `InterviewEngine`:
   - builds prompt (Builder + Strategy + transcript),
   - streams Gemini reply token-by-token (Observer),
   - appends turns, advances the state machine on a **server-authoritative timer**
     + turn budget. Approaching the deadline → `WRAP_UP`.
   - Voice: client uses Web Speech `SpeechRecognition` (mic → text over WS) and
     `speechSynthesis` (speaks interviewer text). Toggleable; text always works.
3. **Evaluation** — at `COMPLETE`, `EvaluationService` sends transcript + rubric to
   Gemini requesting **structured JSON** (schema-constrained; a repair fallback
   re-prompts if JSON is malformed). Produces `Evaluation`, persisted.
4. **Result** — `GET /api/sessions/{id}/result` → summary, score gauge, verdict.

### Rubric (weights vary by seniority via Strategy)
Technical depth · Problem-solving · Communication · Experience relevance · Behavioral/culture.
`move_forward = overall_score >= threshold(seniority)` combined with the LLM's
categorical recommendation.

## 7. API Surface

### Actors & two-step flow
- **Admin** configures master settings and creates an **Invite** (`POST /api/invites`),
  then shares the link `/invite/{id}`.
- **Candidate** opens the link, sees the role, submits **only** their profile
  (GitHub/LinkedIn/resume) via `POST /api/invites/{id}/start`, which creates the
  session and begins the interview.
- (`POST /api/sessions` remains as a one-step admin path for direct use/testing.)
- *Admin authentication is out of scope for the scaffold — see roadmap.*

**Auth:** admin endpoints require a bearer token from `POST /api/admin/login`
(single shared `ADMIN_PASSWORD` → HMAC-signed 12h token). Candidate endpoints
(invite view/start, WebSocket, finish, feedback) are public via the invite link.

**LLM provider** is selectable via `LLM_PROVIDER` (`anthropic` | `gemini` | `mock`
| `auto`) behind the `LLMProvider` Factory — Claude Haiku 4.5 (~$0.07/interview)
or Gemini free tier.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/admin/login` | public | Exchange admin password for a bearer token |
| `POST` | `/api/invites` | admin | Create an invite from master settings |
| `GET` | `/api/invites` | Admin: list all invites + session counts (dashboard) |
| `GET` | `/api/sessions` | Admin: list session summaries (score/verdict/feedback) |
| `GET` | `/api/invites/{id}` | Candidate: view invite (role, seniority, duration) |
| `POST` | `/api/invites/{id}/start` | Candidate: submit profile → create session |
| `POST` | `/api/sessions` | One-step: create session from config + profile |
| `GET` | `/api/sessions/{id}` | Session status/state |
| `WS` | `/api/ws/interview/{id}` | Live interview stream |
| `POST` | `/api/sessions/{id}/finish` | Force wrap-up + trigger evaluation |
| `POST` | `/api/sessions/{id}/finish` | Force wrap-up + evaluation (idle/deadline) |
| `GET` | `/api/sessions/{id}/result` | Final evaluation |
| `POST` | `/api/sessions/{id}/feedback` | Post-interview feedback (rating 1-5 + comment) to mature the product |

WebSocket message envelope (JSON):
`{type: "candidate_msg"|"interviewer_token"|"state"|"error"|"done", ...}`

## 8. Free Resources
- **Gemini** free tier: default `gemini-2.0-flash`.
- **GitHub** public REST API (unauthenticated ~60 req/hr; optional token raises it).
- **Web Speech API** (Chrome/Edge) — free STT + TTS.
- **SQLite** — embedded, zero-config.

## 9. Error Handling & Resilience
- Profile adapters isolated; partial context is acceptable.
- Gemini call retries with backoff; evaluation JSON has a repair pass.
- Timer is server-authoritative; WebSocket supports reconnect (state rehydrated
  from the repository).
- Missing `GEMINI_API_KEY` → clear startup error and a mock provider fallback for
  local UI testing.

## 10. Testing
- `pytest`: state-machine transitions, strategy weight tables, rubric JSON
  parsing + repair, profile adapters with mocked HTTP/PDF.
- Manual: end-to-end interview via the UI with a real Gemini key.

## 11. Deployment
- **Dev:** `docker compose up` → backend (`:8000`) + frontend dev server (`:5173`).
- **Prod:** `npm run build` → `frontend/dist` served by FastAPI `StaticFiles`
  (single origin), per FastAPI's serving-a-frontend guidance.
