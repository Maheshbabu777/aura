# AURA - Personal AI Operating System

## Project Overview

AURA is a privacy-first, autonomous personal AI assistant that runs locally on consumer laptops (16GB RAM). It monitors Gmail and Calendar, tracks long-term goals with adaptive replanning, and operates autonomously via scheduled heartbeat tasks.

**Current Status**: Week 1 Complete (Tool Calling Validation Passed at 82.5%)  
**Next Phase**: Week 2 - Memory Agent Implementation  
**Timeline**: 22 weeks total

## Technology Stack

### Backend
- **Runtime**: Python 3.11+
- **Agent Framework**: LangGraph 0.2.x (multi-agent orchestration)
- **API Server**: FastAPI + WebSockets
- **Task Scheduler**: APScheduler 3.10.x

### AI Models
- **Local Model**: Gemma 4 E4B via Ollama (4-bit quantized, ~5GB RAM)
  - Model name: `gemma4:e2b`
  - Used for: Tool calling, classification, routine tasks
  - Base URL: `http://localhost:11434`
- **Cloud Model**: Gemini 3 Flash (Google AI API)
  - Used for: Complex reasoning, brief generation
  - Target cost: ~$0.24/year

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

```
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
│   └── tests/            # Test suite
│
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

### Week 1: LangGraph Validation + Tool Calling ✅
- ✅ Installed dependencies
- ✅ Created validation script with 20 test cases
- ✅ Passed validation at 82.5% (threshold: 70%)
- ✅ Simplified tool set (removed meta-classification tools)
- ✅ Documented scoring rubric

**Key Decisions**:
- Removed `classify_task` and `classify_action` tools (orchestrator handles classification internally)
- Kept 6 core tools: store_memory, search_memory, update_memory, get_calendar, search_emails, schedule_reminder

### Week 2: Memory Agent (Current) 🔄
- [ ] Set up ChromaDB in persistent mode
- [ ] Build MemoryAgent with write_memory and search_memory
- [ ] Connect to LangGraph orchestrator as tool
- [ ] Add loguru structured logging
- [ ] Test persistence across sessions
- [ ] Create pytest fixtures

## Common Commands

### Development
```bash
# Activate environment
conda activate tf-gpu

# Run validation test
python tools/validate_tool_calling.py

# Test Ollama connectivity
python tools/test_ollama.py

# Run tests (future)
pytest tests/ -v --cov=backend

# Start backend (future)
python backend/api/main.py
```

### Git Workflow
- Main branch: `main`
- Commit messages: descriptive, present tense
- Co-authored by: Claude Sonnet 4.5 <noreply@anthropic.com>

## Architecture Principles

### Core Design Decisions
1. **Local-first**: Gemma E4B handles most tasks locally
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
- First Gemma E4B call takes ~10-30s (model loading)

## References

- Project Plan: `aura-project-plan-v3.md`
- Tool Calling Rubric: `docs/validation/tool_calling_rubric.md`
- Validation Results: `validation_results.json` (generated after each test run)
