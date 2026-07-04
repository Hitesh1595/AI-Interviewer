# AI Interviewer — Project TODO

Legend: `[x]` done in scaffold · `[ ]` remaining / iterate later

## Phase 0 — Project setup
- [x] Repo structure (`backend/`, `frontend/`, `docs/`)
- [x] Design spec (`docs/superpowers/specs/2026-07-04-ai-interviewer-design.md`)
- [x] Git init
- [x] Docker Compose + Dockerfiles
- [x] `.env.example` with `GEMINI_API_KEY`, `GEMINI_MODEL`, optional `GITHUB_TOKEN`

## Phase 1 — Backend core (FastAPI)
- [x] `config.py` — settings via pydantic-settings
- [x] `db.py` — SQLModel engine + SQLite session
- [x] `domain/enums.py` — Seniority, InterviewerLevel, InterviewState, Recommendation
- [x] `domain/schemas.py` — InterviewConfig, ProfileFragment, CandidateContext, Turn, Evaluation
- [x] `models/db_models.py` — SessionRecord table
- [x] `repository/session_repo.py` — Repository pattern over SQLite
- [x] `main.py` — app factory, CORS, routers, static mount

## Phase 2 — Design patterns
- [x] **Strategy** — `domain/strategies.py` (seniority + interviewer level → difficulty, rubric weights, tone, question budget)
- [x] **State Machine** — `domain/state_machine.py`
- [x] **LLM Factory + Provider** — `services/llm/{base,gemini,mock,factory}.py`
- [x] **Profile Adapters** — `services/profile/{base,github,linkedin,resume,aggregator}.py`
- [x] **Prompt Builder** — `services/interview/prompt_builder.py`
- [x] **Dependency Injection** — `api/deps.py`

## Phase 3 — Interview engine + evaluation
- [x] `services/interview/engine.py` — orchestrates turns, streaming, state transitions
- [x] `services/evaluation/evaluator.py` — structured rubric scoring + JSON repair
- [x] `api/sessions.py` — REST: create / get / finish / result / **feedback**
- [x] `api/interview_ws.py` — WebSocket live interview
- [x] Post-interview **feedback** capture (rating + comment) to mature the product
- [x] **Two-role flow**: `api/invites.py` — admin creates invite, candidate starts from link
- [x] `services/intake.py` — shared profile-intake helper; `Invite` entity + repo

## Phase 4 — Frontend (React + Vite + Tailwind)
- [x] Vite + TS + Tailwind config
- [x] `api/client.ts` — REST client (sessions + invites)
- [x] `hooks/useInterviewSocket.ts` — WebSocket streaming
- [x] `hooks/useSpeech.ts` — Web Speech STT + TTS
- [x] `pages/AdminSetupPage.tsx` — admin master settings → shareable invite link
- [x] `pages/InvitePage.tsx` — candidate submits resume/links → starts interview
- [x] `pages/InterviewPage.tsx` — chat UI, timer, voice toggle
- [x] `pages/ResultPage.tsx` — summary, score gauge, verdict, **feedback form**
- [x] `App.tsx` + routing + shared components

## Phase 5 — Tests
- [x] `tests/test_state_machine.py`
- [x] `tests/test_strategies.py`
- [x] `tests/test_evaluator.py` (JSON parse/repair)
- [ ] Profile adapter tests with mocked HTTP/PDF (stretch)
- [ ] Frontend component tests (stretch)

## Phase 6 — Polish / later iterations
- [x] **Admin dashboard** (`/admin`) — lists invites, candidate sessions, scores, verdicts, feedback
- [x] Dashboard **filters** (candidate search, status, decision, by-invite), **pagination**, and **delete** (session + invite w/ cascade)
- [x] Admin-entered **candidate name** flows to dashboard + greeting + result
- [x] Candidate/admin split — candidate sees thank-you+feedback (`/done/:id`), admin sees results (`/result/:id`)
- [x] Sessions linked to invites (`invite_id`)
- [x] **Admin authentication** — password login → HMAC token; dashboard/setup/result gated, candidate flow public
- [x] **Claude (Anthropic) provider** — selectable via `LLM_PROVIDER`; default model `claude-haiku-4-5`
- [ ] Invite options: expiry, single-use, per-candidate tracking
- [ ] Real per-user admin accounts + OAuth (current login is a single shared password)
- [ ] Real GitHub token flow + rate-limit handling UI
- [ ] Session list / history dashboard
- [ ] Export evaluation as PDF
- [ ] Auth + multi-recruiter accounts
- [ ] Swap-in Deepgram/other voice provider (interface already abstracted)
- [ ] Anti-cheat / tab-focus signals
- [ ] Deploy guide (Fly.io / Render free tiers)

## Run
- Dev: `docker compose up` → frontend `:5173`, backend `:8000/docs`
- Local (no Docker): see `README.md`
