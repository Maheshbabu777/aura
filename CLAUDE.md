# AURA - Personal AI Operating System

## Project Overview

AURA is a privacy-first, autonomous personal AI assistant that runs locally on consumer laptops (16GB RAM). It monitors Gmail and Calendar, tracks long-term goals with adaptive replanning, and operates autonomously via scheduled heartbeat tasks.

**Current Status**: Week 5 Complete (Gmail Integration + Email Triage)  
**Next Phase**: Week 6 - Calendar + Morning Brief  
**Timeline**: 22 weeks total

## Technology Stack

### Backend
- **Runtime**: Python 3.11+
- **Agent Framework**: LangGraph 0.2.x (multi-agent orchestration)
- **API Server**: FastAPI + WebSockets
- **Task Scheduler**: APScheduler 3.10.x

### AI Models
- **Local Model**: Gemma 4 E2B via Ollama (4-bit quantized, ~5GB RAM)
  - Model name: `gemma4:e2b`
  - Used for: Simple classification, routine queries (speed not critical)
  - Base URL: `http://localhost:11434`
  - **Known Issue**: `num_predict` parameter causes empty responses - omit and use default token limits
- **Cloud Model**: Gemini 3.5 Flash (Google AI API)
  - Used for: Email triage, complex reasoning, brief generation, time-sensitive tasks
  - Speed: <1 second per request (vs 5-10s local)
  - Model name: `gemini-3.5-flash`
  - Target cost: ~$0.50/year (increased from $0.24 due to email triage)

### Storage
- **Vector DB**: ChromaDB 0.5.x (persistent, local)
- **Metadata**: SQLite (FTS5 for keyword search, audit logs)

### Integrations
- **Email**: Gmail API (OAuth 2.0)
- **Calendar**: Google Calendar API (OAuth 2.0)
- **Search**: Tavily API (web research, optional)

### Frontend (Future)
- React 18 + Vite
- Tailwind CSS
- WebSocket for real-time updates

### Tooling
- **Testing**: pytest + pytest-cov (target >70% coverage by Week 22)
- **Logging**: loguru (structured JSON logs)
- **Validation**: Pydantic schemas
- **Security**: python-dotenv for secrets

## Development Environment

### Python Environment
- **Environment Manager**: conda
- **Active Environment**: `tf-gpu`
- **Activation Command**: `conda activate tf-gpu`

**IMPORTANT**: Always activate the conda environment before running Python commands:
```bash
source C:/Users/mahes/miniconda3/etc/profile.d/conda.sh && conda activate tf-gpu && <command>
```

### Environment Variables
Located in `.env` file (never committed):
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
GEMINI_API_KEY=<key>
```

### Dependencies
See `requirements.txt` for full list. Core dependencies:
- langgraph>=0.2.0
- fastapi>=0.111.0
- chromadb>=0.5.0
- python-dotenv
- loguru
- pytest, pytest-cov
- requests
## Project Structure

aura/
├── backend/
│   ├── agents/           # LangGraph agents (orchestrator, memory, goal, task, etc.)
│   ├── memory/           # ChromaDB + SQLite memory system
│   ├── integrations/     # Gmail, Calendar, Web Search APIs
│   ├── guardrails/       # Green/Yellow/Red action classification
│   ├── heartbeat/        # Scheduled tasks (morning brief, night summary)
│   ├── goals/            # Goal tracking and adaptive replanning
│   ├── api/              # FastAPI routes and WebSocket handlers
│   ├── models/           # Pydantic schemas
│   ├── prompts/          # System prompts (loaded at runtime)
│   ├── config/           # Configuration management
│   └── tests/            # Pytest test suite

## Project Phases & Progress

### Phase 1: Core OS Layer (Weeks 1-4)
- ✅ Local & Cloud model routing (`models/`)
- ✅ Conversation Memory & VectorDB (`agents/memory_agent.py`, `memory/`)
- ✅ Intent Classification & Routing (`agents/orchestrator.py`)

### Phase 2: Integrations (Weeks 5-8)
- ✅ Email Triage Agent & Gmail Integration (`agents/email_triage.py`, `integrations/gmail.py`)
- ✅ Google Calendar Integration (`integrations/calendar.py`)
- ✅ Morning Brief Generator (`heartbeat/morning_brief.py`)
- ✅ Guardrails & Approval Queue (`guardrails/`)
- ⏭️ Week 8 Follow-Up Tracker (Skipped to prioritize Phase 3)

### Phase 3: Goal Tracking (Weeks 9-11)
#### Week 9: Goal Structure + Storage ✅
- ✅ Designed 4-tier goal schema (`Goal -> Milestone -> WeeklyTask -> DailyAction`)
- ✅ Built `GoalStore` with SQLite to store hierarchies
- ✅ Built `GoalAgent` to decompose goals using Cloud Gemini
- ✅ Exposed `/api/goals` FastAPI endpoints

#### Week 10: Adaptive Replanning & Deep Context ✅
- ✅ Added `context` field to Goals to hold large texts like Syllabi
- ✅ Built `AdaptiveReplanner` to condense overdue tasks using Gemini Cloud
- ✅ Exposed `/api/goals/{id}/replan` endpoint
- ✅ Passing tests in `test_replanner.py`

├── tools/                # Validation and testing scripts
│   ├── validate_tool_calling.py
│   └── test_ollama.py
│
├── docs/
│   ├── adr/              # Architecture Decision Records
│   └── validation/       # Test rubrics and validation docs
│
├── scripts/              # Setup and utility scripts
├── frontend/             # React dashboard (future)
├── .env                  # Environment variables (gitignored)
├── requirements.txt
└── aura-project-plan-v3.md
```

## Coding Standards

### General Guidelines
- **No emojis**: User preference - avoid emojis in all code, comments, and communication
- **Measured pace**: Ask for input before proceeding with multiple actions
- **Placeholder data**: Use generic test data (John, University, CompanyX) - NEVER use real personal information in tests or validation scripts

### Python Conventions
- Follow PEP 8 style guide
- Use type hints for function signatures
- Structured logging with loguru
- Pydantic for data validation
- Meaningful variable names (no single letters except loop counters)

### Testing Requirements
- Write pytest tests for all new features
- Use fixtures in `tests/conftest.py`
- Target: >70% code coverage by Week 22
- **CRITICAL**: Use placeholder/generic data in tests, not real personal information
  - Example: "John" not actual names, "University" not actual schools
  - This applies to all validation scripts and test data

### Security
- Never commit `.env` files or API keys
- Use `python-dotenv` for environment variables
- Validate all external inputs with Pydantic
- Log all Gemini API calls for cost tracking

## Week-by-Week Progress

### Week 0: Environment Setup ✅
- Ollama installed with gemma4:e2b
- Gemini API key configured
- Git repo initialized
- Python environment set up

### Week 6: Google Calendar + Morning Brief ✅
- ✅ Built Google Calendar API integration with OAuth 2.0
- ✅ Morning Brief generator combining calendar, emails, and goals
- ✅ Added `GeminiClient` parameter fixes for system instructions
- ✅ Real Calendar testing with OAuth credentials
- ✅ 6 new tests passing (3 calendar, 3 morning brief)
- ✅ Exposed `/api/brief/generate` FastAPI endpoint

**Key Features**:
- Google Calendar API fetches today's and tomorrow's events
- Morning Brief aggregates data and uses Gemini 3.5 Flash for Markdown formatting
- Dynamic fetching of urgent emails directly via `EmailTriageAgent`
- Structured prompt for Morning Brief generation

**Key Decisions**:
- Reused Google Cloud Project from Gmail for Calendar API (no new credentials file needed)
- Opted for cloud Gemini for Morning Brief to ensure high-quality markdown generation, with a fallback available to local models.
- Removed `classify_task` and `classify_action` tools (orchestrator handles classification internally)
- Kept 6 core tools: store_memory, search_memory, update_memory, get_calendar, search_emails, schedule_reminder

### Week 2: Memory Agent ✅
- ✅ Set up ChromaDB + SQLite dual-database architecture
- ✅ Built MemoryStore with CRUD operations
- ✅ Built MemoryAgent with smart explicit intent detection
- ✅ Natural language understanding (store/search/update intents)
- ✅ Entity type auto-classification (Person/Goal/Job/Location/Fact)
- ✅ All 22 tests passing (8 MemoryStore + 14 MemoryAgent)
- ✅ Documented architecture in week2-memory-system-explained.md

**Key Decisions**:
- Smart explicit intent detection using pattern matching
- Dual-database: ChromaDB for semantic search, SQLite for structured queries
- Auto entity classification from natural language

### Week 3: Memory Staleness + Entity Tagging ✅
- ✅ Implement staleness detection with TTL
- ✅ Add memory tagging system with auto-tagging
- ✅ Build memory deduplication using ChromaDB embeddings
- ✅ Memory prioritization logic (importance + recency + access frequency)
- ✅ All 57 new tests passing (9 staleness + 16 tagging + 15 deduplication + 17 prioritization)

**Key Features**:
- TTL-based staleness detection with `is_stale()` check
- Auto-tagging from content patterns (work, personal, urgent, education)
- Tag search with AND/OR logic
- Deduplication using similarity threshold (default 0.95)
- Priority scoring: 0-100 points based on importance, recency, access frequency, staleness penalty
- Access tracking: `access_count` and `last_accessed_at` fields

### Week 4: Orchestrator + API ✅
- ✅ Built OrchestratorAgent with intent classification
- ✅ Load prompts from files at runtime
- ✅ Route complex intents to Gemini 3 Flash
- ✅ Built FastAPI app with /chat, /logs, /health endpoints
- ✅ End-to-end test: question → orchestrator → memory agent → answer
- ✅ 14 orchestrator tests passing
- ✅ 91% test coverage (exceeds >50% decision gate)
- ✅ Created docs/architecture.md

**Key Decisions**:
- Local-first: Gemma E2B for routine classification
- Cloud escalation: Gemini 3 Flash for complex reasoning
- Dual model clients: Ollama (local) + Google AI (cloud)
- Structured prompt parsing: INTENT/AGENT/ENTITIES/REASONING format
- FastAPI with CORS for future frontend integration

### Week 5: Gmail Integration + Email Triage ✅
- ✅ Built Gmail API integration with OAuth 2.0
- ✅ Email triage agent with classification (urgent/normal/ignore)
- ✅ Guardrails system with Green/Yellow/Red action rules
- ✅ Store urgent email summaries in memory
- ✅ 57 new tests passing (27 email filter + 14 email triage + 16 guardrails)
- ✅ Real Gmail testing with OAuth credentials
- ✅ Fixed Gemma E2B empty response bug (num_predict parameter issue)
- ✅ Privacy-first email triage: two-stage local pipeline (rule engine + gemma3:1b)

**Key Features**:
- Gmail OAuth flow with token persistence (credentials/gmail_credentials.json + gmail_token.json)
- Two-stage email triage pipeline (privacy-preserving):
  - Stage 1: Rule-based pre-filter (handles ~60-70% of emails instantly, 0ms, no model)
    - Sender pattern matching: noreply@, newsletter@, marketing@, etc. -> IGNORE
    - Subject keyword matching: urgent, deadline, ASAP -> URGENT
    - Configurable VIP sender list -> URGENT
  - Stage 2: Local LLM (gemma3:1b via Ollama, ~1-2s per email, 100% private)
    - Only called for ambiguous emails that pass through rule engine
    - 5x lighter than Gemma E2B (~1GB vs ~5GB RAM)
  - Cloud fallback: Gemini 3.5 Flash available via `email_triage_use_cloud=True` setting
- Priority scoring (1-5) with reasoning
- Automatic memory storage for urgent emails
- Classification source tracking: `rule_engine`, `local_llm`, `cloud_llm`, `fallback`
- Action classification: read (GREEN), draft (YELLOW), send (RED)
- Tested with real Gmail account (mrwantsup@gmail.com)

**Key Decisions**:
- OAuth 2.0 consent screen in "Testing" mode with approved test users
- Restored privacy-first principle: email triage uses local-only pipeline by default
- Two-stage approach: rule engine for obvious emails, lightweight local LLM for ambiguous
- gemma3:1b for email triage (fast, small, capable of simple classification)
- Cloud Gemini is opt-in fallback only (not default) via `email_triage_use_cloud` setting
- Added `model_override` param to OllamaClient.generate() for per-call model selection
- Fixed: Removed num_predict from Ollama calls to avoid empty responses
- Token auto-refresh with 180s timeout for slow networks


## Common Commands

### Development
```bash
# Activate environment
conda activate tf-gpu

# Run validation test
python tools/validate_tool_calling.py

# Test Ollama connectivity
python tools/test_ollama.py

# Run tests
pytest backend/tests/ -v --cov=backend

# Test Gmail authentication
python tools/test_gmail_auth.py

# Test email triage (requires Ollama running)
python tools/test_email_triage_live.py

# Start backend (future)
python backend/api/main.py
```

### Git Workflow

**Branch Strategy**:
- `main` - Stable, tested code only
- `feature/<week-name>` - Development branches for each week
- Never work directly on main after initial setup

**Standard Workflow**:
```bash
# Start new feature
git checkout main
git pull
git checkout -b feature/week3-memory-staleness

# Work, commit, test
git add <files>
git commit -m "feat: description"

# Push and create PR when ready
git push -u origin feature/week3-memory-staleness
# Then create PR on GitHub: feature/week3-memory-staleness → main

# After PR merged, cleanup
git checkout main
git pull
git branch -d feature/week3-memory-staleness
```

**Commit Message Format**:
- Format: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Keep concise (not verbose)
- Always add co-author: `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`

**Current Branch**: `feature/week5-gmail-integration`

## Architecture Principles

### Core Design Decisions
1. **Local-first**: Gemma E2B handles most tasks locally
2. **Cloud escalation**: Complex reasoning → Gemini 3 Flash
3. **Autonomous operation**: Scheduled tasks run without user intervention
4. **Full transparency**: Every action logged and visible in dashboard
5. **Three-tier safety**: Green (auto-execute), Yellow (approval required), Red (blocked)

### Agent Flow
```
User Input / Scheduled Task
         ↓
   Orchestrator Agent
   (Intent Classification)
         ↓
   ┌─────┴─────┬─────────┬──────────┐
   ↓           ↓         ↓          ↓
Memory    Goal      Task      Research
Agent     Agent     Agent     Agent
         ↓
    Guardrails (G/Y/R)
         ↓
    Execute or Queue
```

### Memory System Design
- ChromaDB for semantic search (embeddings)
- SQLite for metadata and FTS5 keyword search
- Entity tagging: Person/Goal/Job/Location/Fact
- Staleness detection with TTL
- Full CRUD operations

## Key Constraints

### Hardware Targets
- Minimum: 16GB RAM
- Tested on: Lenovo Ideapad Slim 3i
- Storage: ~10GB (model + data + dependencies)

### Performance Targets
- Tool calling accuracy: ≥70% (validated)
- Morning brief generation: <30 seconds
- Memory search latency: <2 seconds
- Test coverage: >70% by Week 22

### Cost Targets
- Gemini 3 Flash usage: ~$0.24/year
- Tavily API: optional (skip if free tier exhausted)

## User Preferences

- **Communication style**: Direct, concise, no emojis
- **Pacing**: Measured - ask before proceeding with multiple actions
- **Testing**: Always use placeholder data, never real personal information
- **Environment**: Always use conda tf-gpu environment

## Important Notes

### Decision Gates
- **Week 1 Gate**: Tool calling validation must pass ≥70% before proceeding to Week 2 ✅ PASSED at 82.5%
- **Phase boundaries**: Each phase requires working demo before proceeding

### Testing Philosophy
- Validate at each step (don't batch multiple changes)
- Use real Ollama/Gemini calls in validation (no mocking for integration tests)
- Placeholder data only - protect privacy during development

### Known Issues
- Ollama timeout increased to 120s (model loading can be slow)
- First Gemma E2B call takes ~10-30s (model loading)
- **IMPORTANT**: Do NOT use `num_predict` parameter with Gemma E2B - causes empty responses
- SSL certificate issues on Windows: Set `SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")`

## References

- Project Plan: `aura-project-plan-v3.md`
- Tool Calling Rubric: `docs/validation/tool_calling_rubric.md`
- Validation Results: `validation_results.json` (generated after each test run)
