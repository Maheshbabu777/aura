# AURA - Personal AI Operating System

**Version**: 3.0  
**Timeline**: 22 weeks  
**Status**: Planning

---

## Executive Summary

AURA is a privacy-first, autonomous personal AI assistant that runs locally on consumer laptops (16GB RAM). It monitors Gmail and Calendar, tracks long-term goals with adaptive replanning, and operates autonomously via scheduled heartbeat tasks—all while maintaining full transparency through a real-time dashboard.

**Core Value Proposition**: An AI that manages your life autonomously while keeping you in control, running mostly on-device at near-zero cost (~$0.24/year), with full visibility into every action it takes.

**Target Hardware**: Mid-range laptops (16GB RAM, tested on Lenovo Ideapad Slim 3i)  
**Target Users**: Knowledge workers, students, professionals, freelancers  
**Deployment**: Single-user local application (no multi-tenancy required)

---

## Product Features

### Core Capabilities

1. **Persistent Memory** - Stores information locally with staleness detection and entity tagging
2. **Email Intelligence** - Triages Gmail (urgent/normal/ignore), tracks follow-ups
3. **Calendar Awareness** - Integrates Google Calendar for context-aware scheduling
4. **Morning Brief** - Automated daily summary at 8 AM (calendar + emails + goals)
5. **Night Summary** - End-of-day recap at 10 PM with tomorrow's priorities
6. **Goal Tracking** - Decomposes long-term goals into milestones with adaptive replanning
7. **Web Research** - Configurable daily topic monitoring (optional)
8. **Action Guardrails** - Three-tier safety system (Green/Yellow/Red classification)
9. **Real-Time Dashboard** - Live activity feed, memory browser, goal tracker, approval queue
10. **Autonomous Operation** - Runs on schedule with missed-job recovery and offline fallback

### Key Differentiators

- **Privacy-first**: Local-first architecture with explicit cloud escalation
- **Adaptive planning**: Replans goals when you fall behind (no other tool does this)
- **Full transparency**: Real-time activity feed shows every agent action
- **Near-zero cost**: ~$0.24/year in API costs with Gemini 3 Flash free tier
- **Autonomous**: Works overnight without manual triggers

---

## System Architecture

### Technology Stack

```yaml
Backend:
  Runtime: Python 3.11+
  Agent Framework: LangGraph 0.2.x
  API Server: FastAPI + WebSockets
  Task Scheduler: APScheduler 3.10.x
  
Models:
  Local: Gemma 4 E4B (Ollama, 4-bit quantized, ~5GB RAM)
  Cloud: Gemini 3 Flash (Google AI API, reasoning tasks)
  
Storage:
  Vector DB: ChromaDB 0.5.x (persistent, local)
  Metadata: SQLite (FTS5 for keyword search, audit logs)
  
Integrations:
  Email: Gmail API (direct, OAuth 2.0)
  Calendar: Google Calendar API (direct, OAuth 2.0)
  Search: Tavily API (web research, optional)
  
Frontend:
  Framework: React 18 + Vite
  Styling: Tailwind CSS
  State: React Query + WebSocket hooks
  
Security:
  Secrets: python-dotenv (.env, never committed)
  Validation: Pydantic schemas
  Logging: loguru (structured JSON logs)

Testing:
  Framework: pytest + pytest-cov
  Coverage Target: >70% by Week 22
  CI: GitHub Actions (lint + test on every push)
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       React Dashboard                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Activity    │ │   Memory    │ │    Goal     │           │
│  │   Feed      │ │   Browser   │ │   Tracker   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Approval   │ │ Integration │ │    Logs     │           │
│  │   Queue     │ │   Status    │ │   Viewer    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket + REST API
┌────────────────────────┴────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              LangGraph Agent Layer                   │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │Orchestrator │  │ Memory Agent │  │ Goal Agent │ │   │
│  │  └─────────────┘  └──────────────┘  └────────────┘ │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │ Task Agent  │  │Research Agent│  │Email Triage│ │   │
│  │  └─────────────┘  └──────────────┘  └────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Guardrails  │  │  Heartbeat   │  │ Integrations │     │
│  │   (G/Y/R)    │  │  Scheduler   │  │ Gmail/Cal/Web│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                   Storage Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   ChromaDB   │  │    SQLite    │  │    Ollama    │     │
│  │(Vector Store)│  │(Audit/FTS5)  │  │(Gemma E4B)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                         │
                    Google APIs
              ┌──────────┴──────────┐
         Gemini 3 Flash         Gmail/Calendar
```

### Agent Flow

```
User Input / Scheduled Task
         │
         ▼
   Orchestrator Agent
   (Intent Classification)
         │
         ├─────────────┬─────────────┬─────────────┐
         ▼             ▼             ▼             ▼
   Memory Agent   Goal Agent   Task Agent   Research Agent
         │             │             │             │
         └─────────────┴─────────────┴─────────────┘
                       │
                  Guardrails
             (Green/Yellow/Red)
                       │
                ┌──────┴──────┐
                ▼             ▼
            Execute      Approval Queue
                            (Yellow actions)
```

---

## Project Structure

```
aura/
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py          # Routes tasks to correct agent
│   │   ├── memory_agent.py          # Store/retrieve/search memories
│   │   ├── goal_agent.py            # Goal tracking + replanning
│   │   ├── task_agent.py            # Execute actions via APIs
│   │   ├── email_triage.py          # Email classification
│   │   └── research_agent.py        # Web search + summarization
│   │
│   ├── memory/
│   │   ├── store.py                 # ChromaDB + SQLite wrapper
│   │   ├── staleness.py             # Staleness detection
│   │   └── entities.py              # Entity tagging (Person/Goal/Job)
│   │
│   ├── integrations/
│   │   ├── gmail.py                 # Gmail API client
│   │   ├── calendar.py              # Google Calendar API client
│   │   └── search.py                # Tavily API client (optional)
│   │
│   ├── guardrails/
│   │   ├── classifier.py            # G/Y/R action classification
│   │   ├── rules.py                 # Classification rules
│   │   ├── approval_queue.py        # Yellow action queue
│   │   └── audit_log.py             # SQLite action history
│   │
│   ├── heartbeat/
│   │   ├── scheduler.py             # APScheduler setup
│   │   ├── missed_jobs.py           # Startup recovery
│   │   ├── morning_brief.py         # 8 AM daily brief
│   │   └── night_summary.py         # 10 PM recap
│   │
│   ├── goals/
│   │   ├── models.py                # Goal → Milestone → Task schema
│   │   ├── tracker.py               # Progress monitoring
│   │   └── replanner.py             # Adaptive replanning logic
│   │
│   ├── api/
│   │   ├── main.py                  # FastAPI app + startup hooks
│   │   ├── routers/
│   │   │   ├── memory.py
│   │   │   ├── goals.py
│   │   │   ├── actions.py
│   │   │   ├── heartbeat.py
│   │   │   └── chat.py
│   │   └── websocket.py
│   │
│   ├── models/
│   │   ├── local.py                 # Ollama client (Gemma E4B)
│   │   ├── cloud.py                 # Gemini 3 Flash client
│   │   └── mock.py                  # Test fixtures
│   │
│   ├── prompts/
│   │   ├── orchestrator.txt
│   │   ├── memory_agent.txt
│   │   ├── goal_agent.txt
│   │   ├── email_triage.txt
│   │   └── action_classifier.txt
│   │
│   ├── config/
│   │   ├── settings.py              # Pydantic settings from .env
│   │   ├── constants.py             # Action types, thresholds
│   │   └── logging.py               # loguru configuration
│   │
│   └── tests/
│       ├── conftest.py              # pytest fixtures
│       ├── test_memory.py
│       ├── test_agents.py
│       ├── test_guardrails.py
│       ├── test_goals.py
│       └── test_integrations.py
│
├── frontend/
│   ├── src/
│   │   ├── features/
│   │   │   ├── activity-feed/
│   │   │   ├── memory-browser/
│   │   │   ├── goal-tracker/
│   │   │   ├── approval-queue/
│   │   │   └── audit-trail/
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── api/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│   ├── architecture.md
│   ├── api-reference.md
│   ├── user-guide.md
│   └── adr/                         # Architecture Decision Records
│       ├── 001-language.md
│       ├── 002-langgraph.md
│       ├── 003-local-model.md
│       └── ...
│
├── scripts/
│   ├── setup.sh                     # One-command environment setup
│   ├── start.sh                     # Start backend + frontend
│   └── reset_memory.py              # Wipe and restart memory
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

## Implementation Plan

### Phase 0: Environment Setup (Week 0)

**Goal**: Validate environment before writing code.

**Tasks**:
- [ ] Install Ollama, pull `gemma2:4b-instruct-q4_K_M`
- [ ] Test Ollama: `ollama run gemma2:4b-instruct-q4_K_M "Hello"`
- [ ] Install Python 3.11+ with `uv`
- [ ] Get Gemini 3 Flash API key (Google AI Studio)
- [ ] Test Gemini API with curl
- [ ] Create `.env` with `GEMINI_API_KEY`, `OLLAMA_BASE_URL`
- [ ] Initialize git repo, push to GitHub

**Exit Criteria**: Both Ollama and Gemini respond successfully.

---

### Phase 1: Foundation (Weeks 1-4)

**Goal**: Working local AI with persistent memory.

#### Week 1: LangGraph Validation + Tool Calling Test

**Tasks**:
- [ ] Activate conda environment: `conda activate aura` (or your env name)
- [ ] Install deps: `pip install -r requirements.txt`
- [ ] Complete LangGraph multi-agent tutorial
- [ ] Create `tools/validate_tool_calling.py`:
  - 20 test cases with ground truth
  - Scoring: correct tool (5pts), correct params (3pts), valid JSON (2pts)
  - Pass threshold: ≥70% average
- [ ] Run validation against Gemma E4B
- [ ] Create `backend/prompts/orchestrator.txt`
- [ ] Document rubric in `docs/validation/tool_calling_rubric.md`

**Exit Criteria**: Gemma E4B scores ≥70% on tool-calling validation.

#### Week 2: Memory Agent (Store + Retrieve)

**Tasks**:
- [ ] Set up ChromaDB in persistent mode (`backend/memory/store.py`)
- [ ] Build `MemoryAgent`:
  - `write_memory(text, entity_type, metadata)`
  - `search_memory(query, top_k=5)`
- [ ] Connect to LangGraph orchestrator as tool
- [ ] Add loguru structured logging
- [ ] Test persistence across sessions
- [ ] Create pytest fixtures in `tests/conftest.py`

**Tests**: Tell AURA your name/goals, restart, ask back—confirm persistence.

#### Week 3: Memory Staleness + Entity Tagging

**Tasks**:
- [ ] Add `created_at`, `updated_at`, `ttl_days` to memories
- [ ] Build `staleness_detector.py`: flag memories older than TTL
- [ ] Add entity tagging: Person/Goal/Job/Location/Fact
- [ ] Create `scripts/migrate_db_template.py` for schema changes
- [ ] Write `tests/test_memory.py`: staleness detection, entity tagging

**Tests**: Update a memory, confirm old version flagged stale.

#### Week 4: Orchestrator + API + Testing

**Tasks**:
- [ ] Build `OrchestratorAgent` with intent classification:
  - `store_memory | retrieve_memory | task_request | goal_request`
- [ ] Load `prompts/orchestrator.txt` at runtime
- [ ] Route complex intents to Gemini 3 Flash
- [ ] Log all Gemini payloads
- [ ] Build FastAPI app with `/chat` endpoint
- [ ] Add `/logs` endpoint (last 100 lines)
- [ ] End-to-end test: question → orchestrator → memory agent → answer
- [ ] Write pytest tests for orchestrator routing
- [ ] Create `docs/architecture.md`

**Exit Criteria**: >50% test coverage on `backend/agents/` and `backend/memory/`.

**Milestone**: Push to GitHub with architecture diagram in README.

---

### Phase 2: Integrations (Weeks 5-8)

**Goal**: AURA reads email and calendar. First real-world utility.

#### Week 5: Gmail Integration + Email Triage

**Tasks**:
- [ ] Research Gmail API OAuth flow
- [ ] Build `integrations/gmail.py`: OAuth + fetch unread emails
- [ ] Define classification rules in `guardrails/rules.py`:
  - Green = read/summarize
  - Yellow = draft reply
  - Red = send without approval
- [ ] Build email triage: fetch → classify (urgent/normal/ignore) → store summaries
- [ ] Use Gemma locally for classification
- [ ] Test on real inbox for 3 days, tune prompts
- [ ] Write `tests/test_integrations.py`

**User Validation**: Run email triage on real inbox. Judge accuracy. Iterate.

#### Week 6: Google Calendar + Morning Brief

**Tasks**:
- [ ] Research Calendar API OAuth flow
- [ ] Build `integrations/calendar.py`: fetch today + tomorrow events
- [ ] Build `MorningBriefGenerator` in `heartbeat/morning_brief.py`:
  - Inputs: calendar events + urgent emails + goal status
  - Output: structured markdown brief
- [ ] Use Gemini 3 Flash for brief quality (log token usage)
- [ ] Load `prompts/morning_brief.txt`
- [ ] Test manually daily for 1 week
- [ ] Expose `/api/brief` endpoint

**User Validation**: Use morning brief daily for 1 week. Grade quality.

#### Week 7: Guardrails + Approval Queue

**Tasks**:
- [ ] Build `guardrails/classifier.py`: tag actions Green/Yellow/Red
- [ ] Load rules from `classifier_rules.py`
- [ ] Build `ApprovalQueue`: Yellow actions pause, await `/api/approve` or `/api/reject`
- [ ] Build `AuditLog`: SQLite table with timestamp + reasoning
- [ ] Add rollback for reversible Yellow actions
- [ ] Test: instruct AURA to send email, confirm it waits for approval
- [ ] Write `tests/test_guardrails.py`

**Tests**: Trigger Yellow action. Confirm approval flow works.

#### Week 8: Follow-Up Tracker + Phase Milestone

**Tasks**:
- [ ] Build `FollowUpTracker`: detect threads in email history
- [ ] Categorize: things you're waiting on vs. things you owe
- [ ] Add follow-up summary to morning brief
- [ ] Full pipeline test: real Gmail + Calendar for 3 consecutive days
- [ ] Review `/api/logs`, debug failures
- [ ] Record 2-minute demo video
- [ ] Push to GitHub with demo link in README

**Milestone**: Email triage + morning brief working end-to-end.

---

### Phase 3: Goal Tracking (Weeks 9-11)

**Goal**: Long-horizon goal tracking with adaptive replanning.

#### Week 9: Goal Structure + Storage

**Tasks**:
- [ ] Design goal schema in `goals/models.py`:
  - `Goal → List[Milestone] → List[WeeklyTask] → List[DailyAction]`
  - Fields: title, deadline, priority, status, dependencies, progress_pct
- [ ] Build `GoalAgent`:
  - `create_goal()`, `update_progress()`, `get_status()`, `list_goals()`
- [ ] Store in ChromaDB + SQLite for structured queries
- [ ] Use Gemini 3 Flash for goal decomposition
- [ ] Load `prompts/goal_agent.txt`
- [ ] Test: enter "get ML Engineer role by September", confirm breakdown
- [ ] Write `tests/test_goals.py`

**Tests**: Create goal, verify milestones and weekly tasks generated correctly.

#### Week 10: Progress Monitoring + Adaptive Replanning

**Tasks**:
- [ ] Build `ProgressTracker` in `goals/tracker.py`:
  - Compare planned vs. completed weekly
  - Detect: on_track / falling_behind / at_risk
- [ ] Build `adaptive_replan()` in `goals/replanner.py`:
  - Redistribute tasks if week missed
  - Never push deadline without user confirmation
- [ ] Build fallback: when no valid replan exists, ask user to adjust deadline
- [ ] Wire goal progress into morning brief
- [ ] Test edge case: 3 weeks behind on 4-week goal → confirm asks for adjustment
- [ ] Write tests for replanning edge cases

**Tests**: Mark week as missed, verify redistribution. Test fallback logic.

#### Week 11: Night Summary + Goal API + Phase Milestone

**Tasks**:
- [ ] Build `NightSummaryAgent` in `heartbeat/night_summary.py`:
  - Inputs: completed tasks + missed tasks + tomorrow's calendar
  - Output: what got done, what didn't, priorities for tomorrow
- [ ] Load `prompts/night_summary.txt`
- [ ] Trigger manually (scheduler comes in Phase 5)
- [ ] Test full daily loop for 3 days: morning brief → work → night summary
- [ ] Expose goal endpoints in `api/routers/goals.py`:
  - `GET /goals`, `POST /goals`, `PUT /goals/{id}/progress`, `GET /goals/{id}/plan`
- [ ] Document goal tracking in README
- [ ] Record demo: enter goal → show breakdown → simulate progress → replan

**User Validation**: Use night summary for 2 weeks. Decide if keeping it.

**Milestone**: Goal tracking with adaptive replanning working.

---

### Phase 4: Dashboard (Weeks 12-15)

**Goal**: React dashboard makes AURA feel like a real product.

#### Week 12: React Scaffold + Real-Time Activity Feed

**Tasks**:
- [ ] Bootstrap: `npm create vite@latest frontend -- --template react`
- [ ] Install Tailwind CSS, configure PostCSS
- [ ] Set up FastAPI WebSocket in `api/websocket.py`
- [ ] Build `ActivityFeed` component: real-time agent action stream
- [ ] Style with Green/Yellow/Red color indicators
- [ ] Test: ask AURA a question, confirm actions appear in feed

**Tests**: Open dashboard while interacting with AURA. Verify real-time updates.

#### Week 13: Memory Browser + Logs Viewer

**Tasks**:
- [ ] Build `MemoryBrowser`: search input + results list
- [ ] Display: content, entity type, created_at, staleness indicator
- [ ] Build `MemoryEditModal`: edit or delete memories
- [ ] Add entity type filter (People, Goals, Jobs, etc.)
- [ ] Add staleness banner with "Update or dismiss" action
- [ ] Build `LogsViewer`: connects to `/api/logs`, shows live stream
- [ ] Add log level filter (INFO/WARNING/ERROR)

**Tests**: Browse memories after 2 weeks of use. Edit stale memory.

#### Week 14: Goal Tracker + Approval Queue

**Tasks**:
- [ ] Build `GoalTracker`:
  - Goal cards with progress bars
  - Milestone timeline (on-track indicator: green/amber/red)
  - Weekly task checklist
- [ ] Build `ApprovalQueue`:
  - Pending Yellow actions list
  - Approve/Reject buttons → `/api/approve`, `/api/reject`
  - Show reasoning for each action
- [ ] Wire to FastAPI with loading states

**Tests**: Create goal, mark tasks complete. Trigger Yellow action, approve via UI.

#### Week 15: Integration Status + Polish + Phase Milestone

**Tasks**:
- [ ] Build `IntegrationStatus` panel: which services connected + last sync time
- [ ] Show "Gmail: active (synced 2m ago)" status
- [ ] Fix responsive layout for mobile
- [ ] Add error boundaries and fallback states
- [ ] Write Docker Compose: starts backend + serves frontend build
- [ ] Record 3-minute demo: all panels with real data
- [ ] Add demo GIFs to README

**Milestone**: Full dashboard with all panels working.

---

### Phase 5: Autonomous Operation (Weeks 16-19)

**Goal**: AURA runs autonomously overnight.

#### Week 16: Audit Trail + Heartbeat Scheduler Setup

**Tasks**:
- [ ] Build `AuditTrail` component: paginated action history
- [ ] Add filters: action type (G/Y/R), date range, agent
- [ ] Wire to `/api/actions/history`
- [ ] Build `heartbeat/scheduler.py` with APScheduler:
  - `morning_brief`: cron, 8:00 AM daily
  - `email_check`: interval, every 2 hours
  - `goal_progress_update`: cron, 9:00 PM daily
  - `night_summary`: cron, 10:00 PM daily
- [ ] Add `HeartbeatStatus` panel to dashboard: next run times
- [ ] Test: leave AURA running overnight, check 8 AM brief fires

**Tests**: Overnight test. Verify morning brief runs at 8 AM.

#### Week 17: Missed Jobs Recovery + Reliability

**Tasks**:
- [ ] Build `heartbeat/missed_jobs.py`:
  - `check_missed_jobs_on_startup()`
  - If morning brief missed, generate immediately with "[Delayed]" tag
  - Skip missed night summaries (no value running yesterday's recap)
- [ ] Call from `api/main.py` on FastAPI startup
- [ ] Add retry logic with exponential backoff
- [ ] Implement offline fallback: if Gemini unreachable, use Gemma + "[offline mode]" flag
- [ ] Test: stop AURA at 7 AM, restart at 9 AM → confirm delayed brief
- [ ] Test: disconnect internet → confirm graceful degradation

**Tests**: Simulate missed job. Verify recovery on startup.

#### Week 18: Web Research Agent (Optional)

**Tasks**:
- [ ] Configure Tavily API (free tier: 1000 searches/month)
- [ ] Build `ResearchAgent` in `agents/research_agent.py`:
  - `search(query)` → fetch → summarize → store
- [ ] Make configurable: "Topics to track: [empty by default]"
- [ ] Add research summaries to morning brief as "News" section
- [ ] Load `prompts/research_agent.txt`
- [ ] Test: configure "Krutrim AI news" tracking for 3 days
- [ ] Write `tests/test_research.py`

**User Validation**: Test web research for 3 days. Decide if keeping it.

#### Week 19: 24-Hour Autonomous Test + Phase Milestone

**Tasks**:
- [ ] Full 24-hour autonomous test: no manual interaction
- [ ] Review all heartbeat outputs: morning brief, email checks, goal updates, night summary
- [ ] Check `/api/logs` for errors/warnings
- [ ] Fix all reliability issues found
- [ ] Add uptime metrics to dashboard
- [ ] Update `HeartbeatStatus`: last run, next run, success rate
- [ ] Record demo: AURA running autonomously with live dashboard

**Exit Criteria**: 24-hour autonomous test passes without manual intervention.

**Milestone**: AURA operates autonomously.

---

### Phase 6: Production Readiness (Weeks 20-22)

**Goal**: Turn working system into portfolio-grade artifact.

#### Week 20: Security Hardening

**Tasks**:
- [ ] Audit secrets: ensure all in `.env`, verify not in git history
  - `git log --all -p | grep -i "api_key"`
- [ ] Add rate limiting to FastAPI (slowapi)
- [ ] Review audit log completeness
- [ ] Test approval queue: attempt to bypass Yellow actions
- [ ] Run security scan: `bandit backend/` → fix HIGH severity issues
- [ ] Document security model in `docs/security.md`

**Tests**: Pen-test approval queue. Run bandit security scan.

#### Week 21: Performance + Cost Verification

**Tasks**:
- [ ] Profile Gemini API call frequency over 1 week
- [ ] Identify calls that can use Gemma locally
- [ ] Add response caching (1-hour window for identical calls)
- [ ] Measure actual token cost → confirm ~$0.24/year estimate
- [ ] Document cost breakdown in README
- [ ] RAM profiling: confirm 7GB peak on target hardware
- [ ] Optimize ChromaDB query latency (add indexes if needed)
- [ ] Load test: 100 concurrent `/chat` requests

**Tests**: Week-long cost monitoring. Load testing.

#### Week 22: Documentation + Launch

**Tasks**:
- [ ] Write complete README:
  - What AURA is + demo GIF
  - Architecture diagram
  - One-command setup: `./scripts/setup.sh`
  - Configuration reference (all `.env` variables)
  - How to add integrations guide
- [ ] Write ADRs in `docs/adr/` (one per major decision)
- [ ] Write `docs/how-to/add-agent.md`
- [ ] Add `CONTRIBUTING.md` with issue templates
- [ ] Set up GitHub Actions: lint (ruff) + test (pytest) + coverage report
- [ ] Run full test suite: confirm >70% coverage
- [ ] Publish to GitHub with MIT license
- [ ] Add GitHub topics: `ai`, `personal-assistant`, `langgraph`, `gemini`, `local-first`
- [ ] Record 5-minute demo video, upload to YouTube
- [ ] Write LinkedIn post: "Built a personal AI OS in 22 weeks"
- [ ] Post to r/LocalLLaMA, r/selfhosted, Hacker News Show HN

**Milestone**: Public launch. Portfolio-ready.

---

## Decision Gates

Critical checkpoints where you **must** achieve stated outcome before proceeding:

### Gate 1: Week 0 → Week 1
**Requirement**: Ollama and Gemini API both respond successfully  
**Test**: `ollama run gemma2:4b-instruct-q4_K_M "Hello"` + curl to Gemini API  
**Why**: Week 1 is for LangGraph validation, not environment debugging

### Gate 2: Week 1 → Week 2
**Requirement**: Gemma E4B tool-calling validation score ≥70%  
**Test**: `python tools/validate_tool_calling.py` produces ≥70% across 20 cases  
**Why**: Memory agent depends on reliable tool calling. If foundation is broken, everything built on top will be broken.

### Gate 3: Week 4 → Week 5
**Requirement**: >50% test coverage on `agents/` and `memory/`  
**Test**: `pytest --cov=backend/agents --cov=backend/memory`  
**Why**: Entering integration phase without tests means regressions won't be caught until later when expensive to fix.

### Gate 4: Week 5 → Week 6
**Requirement**: Gmail integration works end-to-end  
**Test**: Fetch 10 unread emails → classify → store summaries in MemoryAgent  
**Why**: Calendar integration follows same pattern. If Gmail is broken, Calendar will also be broken.

### Gate 5: Week 10 → Week 11
**Requirement**: Goal Agent handles edge case: 3 weeks behind on 4-week goal  
**Test**: Create goal with 4-week deadline, mark weeks 1-3 missed, trigger replan → system asks user to adjust deadline  
**Why**: Dashboard phase requires reliable goal tracking. Edge cases surface in production.

### Gate 6: Week 19 → Week 20
**Requirement**: 24-hour fully autonomous test passes  
**Test**: Leave AURA running 8 AM Day 1 → 8 AM Day 2 with no interaction  
**Why**: Can't ship a system that doesn't run autonomously.

---

## Risk Management

### Critical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Local model fails tool-calling validation | High | High | Week 1 validation test with 70% pass threshold. If fails, adjust prompting or switch to Gemma 9B before proceeding. |
| LangGraph learning curve delays Phase 1 | Medium | Medium | Week 0 dedicated to environment setup. Week 1 entirely on LangGraph tutorial before building AURA logic. |
| Gmail/Calendar API auth breaks | Medium | Medium | Test OAuth flow early (Week 5-6). Use official Google SDKs. Document auth setup thoroughly. |
| Scope creep | High | High | Phase 1-3 is MVP. Write new feature ideas to `docs/BACKLOG.md` instead of building. Protect timeline. |
| Gemini free tier rate limits | Low | Low | Use `backend/models/mock.py` for tests. Protects rate limits and speeds up tests 10x. |
| Adaptive replanning fails edge cases | Medium | Medium | Test explicitly: missed all weeks, conflicting goals, impossible deadline. Build fallback to ask user. |
| Missed heartbeat jobs after laptop sleep | High | Medium | Week 17: startup recovery checks missed jobs, generates delayed briefs. Dead simple: check last run time on boot. |
| No observability for overnight runs | High | High | Week 4: loguru + `/api/logs`. Week 13: LogsViewer UI. Review logs each morning. |

### Assumptions

- **Target hardware**: 16GB RAM laptop, typically plugged in
- **Internet**: Always available (offline fallback is graceful degradation, not primary mode)
- **User profile**: Technical user comfortable with Python/Node.js setup
- **Single-user**: No multi-tenancy, no concurrent users
- **Privacy**: User trusts Google APIs (Gmail/Calendar/Gemini are all Google)

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Peak RAM usage | <7GB | memory_profiler during full day operation |
| Morning brief latency | <10s | Time from 8:00:00 to brief complete |
| Email triage (10 emails) | <15s | Fetch + classify + store |
| Goal replan | <20s | Gemini 3 Flash call + update storage |
| Dashboard load time | <2s | First contentful paint |
| Memory search | <500ms | p95 ChromaDB query latency |
| API monthly cost | <$0.02 | Gemini 3 Flash free tier (~5 calls/day) |
| Test coverage | >70% | pytest-cov on backend/ |

---

## Success Metrics

### Technical Metrics (Week 22)
- [ ] All decision gates passed
- [ ] >70% test coverage
- [ ] 24-hour autonomous operation without failures
- [ ] <7GB RAM usage
- [ ] Security audit passed (no HIGH severity issues)

### Product Metrics (Post-Launch)
- [ ] Daily active usage (personally dogfooding)
- [ ] Morning brief checked 5+ days/week
- [ ] At least 1 goal actively tracked with adaptive replanning
- [ ] Zero unauthorized actions (approval queue never bypassed)
- [ ] GitHub stars >50 within 1 month

### Career Metrics
- [ ] Demo-ready project for interviews (Week 15)
- [ ] Portfolio artifact on GitHub (Week 22)
- [ ] LinkedIn post engagement >100 interactions
- [ ] Interview requests from target companies (Krutrim, Gnani.ai, Sprinklr)

---

## Development Guidelines

### Code Quality

- **Testing**: Write tests for every agent, integration, and guardrail. Use fixtures for mocked LLM responses.
- **Logging**: Every agent action must log with structured context (agent name, input, output, duration).
- **Prompts**: Store in `backend/prompts/*.txt`, load at runtime. Never hardcode in Python.
- **Schemas**: Use Pydantic for all data models. Validate API inputs/outputs.
- **Error Handling**: Graceful degradation. Offline mode when Gemini unreachable.

### Git Workflow

- **Commits**: One feature per commit. Write clear messages: `feat: add email triage classifier`
- **Branches**: `main` for stable, `dev` for active work, feature branches for experiments
- **Never commit**: `.env`, ChromaDB files, `*.key`, logs

### Documentation

- **ADRs**: Write Architecture Decision Record for every major tech choice
- **README**: Keep updated with setup instructions and demo GIFs
- **Code comments**: Only when "why" is non-obvious (constraints, workarounds, invariants)
- **API docs**: FastAPI auto-generates OpenAPI docs at `/docs`

---

## Weekly Checklist Template

Use this for each week to track progress:

```markdown
## Week X: [Phase Name]

**Goal**: [One-sentence goal]

**Completed**:
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Tests Passed**:
- [ ] Unit tests for new features
- [ ] Integration tests for APIs
- [ ] Manual validation (if applicable)

**Blockers**: None / [Describe blocker]

**Decision Gate**: [Pass/Fail] - [Gate requirement if applicable]

**Notes**: [What went well, what to improve next week]
```

---

## Appendix

### A. Environment Setup Commands

```bash
# Install Ollama
# Download from https://ollama.ai (Windows installer)
ollama pull gemma2:4b-instruct-q4_K_M

# You already have project created and conda env
cd C:\Users\mahes\projects\aura

# Activate your conda environment
conda activate aura  # (or whatever you named it)

# Install Python dependencies
pip install -r requirements.txt

# Frontend
npm create vite@latest frontend -- --template react
cd frontend && npm install && npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### B. .env.example

```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
GEMINI_API_KEY=your_gemini_api_key_here

# Google APIs
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
CALENDAR_CLIENT_ID=your_calendar_client_id
CALENDAR_CLIENT_SECRET=your_calendar_client_secret

# Optional Integrations
TAVILY_API_KEY=your_tavily_api_key  # For web research

# Application
LOG_LEVEL=INFO
MEMORY_DB_PATH=./data/chromadb
AUDIT_LOG_PATH=./data/audit.db
```

### C. Useful Commands

```bash
# Development
./scripts/start.sh              # Start backend + frontend
pytest --cov=backend            # Run tests with coverage
ruff check backend/             # Lint code

# Docker
docker-compose up               # Start all services
docker-compose down             # Stop all services

# Database
python scripts/reset_memory.py  # Wipe memory (nuclear option)

# Logs
tail -f logs/aura.log          # Watch live logs
```

### D. Resources

- **LangGraph**: https://python.langchain.com/docs/langgraph
- **FastAPI**: https://fastapi.tiangolo.com
- **ChromaDB**: https://docs.trychroma.com
- **Gemini API**: https://ai.google.dev/docs
- **Gmail API**: https://developers.google.com/gmail/api
- **Calendar API**: https://developers.google.com/calendar/api

---

**Last Updated**: 2026-05-22  
**Status**: Ready for implementation  
**Next Action**: Begin Week 0 environment setup
