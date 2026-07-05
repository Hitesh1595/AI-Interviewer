# 🤖 AI Interviewer

An AI-powered interviewer that ingests a candidate's **GitHub**, **LinkedIn**, and
**PDF resume**, runs a time-boxed **live voice interview** tailored to a target
**role** and **seniority**, then produces a **summary**, a **score out of 10**, and
a **move-forward / no** recommendation. Voice runs over **OpenAI Realtime**
(WebRTC, speech-to-speech); evaluation runs on an **OpenAI** text model. Frontend
is React + Vite + Tailwind.

> Reference/inspiration: [code100x/ai-interviewer](https://github.com/code100x/ai-interviewer).
> This project reimplements the idea in **Python/FastAPI** with a pattern-driven
> stack (no scraping).

## Roles & flow

- **Admin** (`/`) sets the master settings (role, seniority, style, duration, focus)
  and gets a **shareable invite link**.
- **Candidate** (`/invite/{id}`) opens the link, sees the role, adds **only** their
  resume + GitHub/LinkedIn, and the interview starts.
- Interview → evaluation → feedback follow automatically.

## Features

- **Any subset of inputs** — GitHub URL, LinkedIn text/PDF, resume PDF (≥1 required).
- **Profile-grounded questions** — extracts tech stack + real projects and asks
  about *the candidate's actual work* (e.g. "you built X with FastAPI+Postgres…").
- **Role + seniority aware** — intern / junior / senior change difficulty, rubric
  weights, and the pass threshold (Strategy pattern).
- **Real interview shape** — the AI introduces itself, converses naturally with
  follow-ups, wraps up, then evaluates.
- **Structured evaluation** — weighted rubric → overall /10, strengths, weaknesses,
  summary, and hire decision.
- **Post-interview feedback** — candidates rate the experience to help mature the product.

## Architecture & design patterns

Layered: **API → services → domain → persistence**. See the full spec in
[`docs/superpowers/specs/2026-07-04-ai-interviewer-design.md`](docs/superpowers/specs/2026-07-04-ai-interviewer-design.md).

| Pattern | Where |
|---|---|
| Strategy | `domain/strategies.py` (seniority × interviewer level) |
| State Machine | `domain/state_machine.py` |
| Adapter | `services/profile/{github,linkedin,resume}.py` |
| Factory | `services/llm/factory.py`, `services/profile/aggregator.py` |
| Builder | `services/interview/prompt_builder.py` |
| Repository | `repository/session_repo.py` |
| Observer / streaming | `api/interview_ws.py` (WebSocket) |
| Dependency Injection | `api/deps.py` |

## Quick start (Docker Compose — recommended)

```bash
cp .env.example .env
# Paste an OpenAI key:
#   OPENAI_API_KEY=...
#   OPENAI_TEXT_MODEL=gpt-4o-mini        (evaluation)
#   OPENAI_REALTIME_MODEL=gpt-realtime-2 (voice interview)
#   OPENAI_VOICE=alloy
# Also set ADMIN_PASSWORD to protect the dashboard.
docker compose up --build
```

- Admin (login → create invite → dashboard): http://localhost:5173  (sign in with `ADMIN_PASSWORD`)
- Backend docs: http://localhost:8000/docs

> No key? It still runs on a **mock LLM** (canned interview + evaluation) so you can
> click through the UI. Add a key for real interviews.

### LLM provider

Set `LLM_PROVIDER` to `openai` (default) or `mock`. OpenAI powers both the live
voice interview (Realtime API over WebRTC) and the text evaluation model. The
provider is hidden behind an `LLMProvider` interface (Factory pattern) — adding
another is one file.

### Admin login

The dashboard, invite creation, and result pages require an admin token. Sign in at
`/admin/login` with `ADMIN_PASSWORD` (env). Candidate pages (`/invite/{id}`, the
interview, the thank-you screen) are public via the invite link. This is a single
shared password for the scaffold — swap for per-user accounts + OAuth in production.

## Local dev (without Docker)

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # add OPENAI_API_KEY
uvicorn app.main:app --reload
```

**Frontend** (separate terminal)
```bash
cd frontend
npm install
npm run dev                  # proxies /api to http://localhost:8000
```

## Production (single origin)

Build the frontend and let FastAPI serve it (per FastAPI's frontend guide):
```bash
cd frontend && npm run build   # outputs frontend/dist
cd ../backend && uvicorn app.main:app
```
FastAPI serves `frontend/dist` (with SPA fallback) if the folder exists.

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

## How the interview flows

1. **Admin creates invite** (`POST /api/invites`) → shares `/invite/{id}`.
2. **Candidate starts** (`POST /api/invites/{id}/start`) — profile adapters run
   concurrently, failures isolated; context aggregated (tech stack + projects).
3. **Interview** (`POST /api/realtime/token/{id}`) — the backend mints a
   short-lived OpenAI Realtime token bound to this candidate's profile-grounded
   instructions; the browser connects directly to OpenAI over WebRTC for a live
   spoken conversation, paced by the time + turn budget.
4. **Transcript** (`POST /api/realtime/{id}/transcript`) — the browser posts the
   spoken transcript back once the interview ends.
5. **Evaluation** — on wrap-up (or deadline), the transcript is scored via a
   weighted rubric → summary, /10, verdict.
6. **Feedback** (`POST /api/sessions/{id}/feedback`) — rate the experience.

## Free resources

GitHub public REST API · SQLite. (OpenAI text + Realtime voice are paid, usage-billed.)

## Known limitations (scaffold)

- Résumés are stored in plaintext SQLite (fine for local/demo; encrypt for prod).
- OpenAI Realtime voice is paid (usage-billed) — no free-tier voice path.
- LinkedIn PDF parsing is heuristic (export formats vary).
- Voice requires a browser with WebRTC (all modern browsers); no text-only fallback is wired into the UI currently.
- SQLite suits a demo; swap in Postgres via the repository interface for scale.

See [`TODO.md`](TODO.md) for the full project checklist and roadmap.
