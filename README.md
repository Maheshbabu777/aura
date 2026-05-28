# AURA - Personal AI Operating System

**A privacy-first, autonomous AI assistant that runs entirely on your laptop.**

AURA is designed to be your personal AI that monitors your Gmail, manages your calendar, remembers important information about your life, and helps you stay on top of tasks and long-term goals. Unlike cloud-based assistants, AURA runs locally using open-source models (Gemma 4 E2B) for routine tasks, keeping your data private while still leveraging cloud AI (Gemini 3 Flash) only when needed for complex reasoning.

**Hardware Requirements:** Standard laptop with 16GB RAM  
**Privacy:** All data stays local, encrypted at rest, zero telemetry

---

## Current Status: Week 5 Complete

**Phase 1 (Weeks 1-5): Foundation - COMPLETE**

We've completed the foundational infrastructure that powers AURA:

- **Week 1**: Multi-agent orchestration with LangGraph + validated tool calling (82.5% accuracy)
- **Week 2**: Persistent memory system with semantic search (ChromaDB) and structured metadata (SQLite)
- **Week 3**: Advanced memory features - staleness detection, auto-tagging, deduplication, priority scoring
- **Week 4**: Orchestrator agent that routes requests + FastAPI server (91% test coverage)
- **Week 5**: Gmail OAuth integration + AI-powered email triage agent

**Next: Week 6 - Google Calendar Integration + Morning Brief Generation**

---

## What Works Right Now

### 1. Intelligent Memory System
AURA can remember and recall information about your life:

- **Semantic Search**: Ask "What do you know about my job?" and it searches by meaning, not just keywords
- **Auto-Tagging**: Automatically categorizes memories (work, personal, urgent, etc.)
- **Staleness Detection**: Knows when information is outdated (e.g., "I work at TechCorp" has a TTL)
- **Smart Prioritization**: Recent, frequently accessed, and important memories rank higher
- **Deduplication**: Won't store the same fact twice

**Example:**
```
You: "Remember that I work at TechCorp as a software engineer"
AURA: "I've stored that information. Entity type: Job"

You: "What do you know about my job?"
AURA: "You work at TechCorp as a software engineer"
```

### 2. Gmail Integration with Email Triage
AURA connects to your Gmail account and automatically classifies emails:

- **OAuth 2.0 Flow**: Secure authentication with token persistence
- **AI Classification**: Gemini 3.5 Flash classifies each email as urgent/normal/ignore (<1s per email)
- **Priority Scoring**: Assigns 1-5 priority with reasoning
- **Smart Summaries**: Urgent emails are automatically summarized and stored in memory

**How it works:**
1. AURA fetches unread emails from your Gmail
2. For each email, Gemini 3.5 Flash reads subject/sender/preview
3. Classifies as URGENT (deadlines, meetings), NORMAL (updates), or IGNORE (newsletters)
4. Urgent emails are flagged and their summaries stored for quick recall

**Example Classification:**
- Email: "Meeting tomorrow at 9 AM" from boss → **URGENT** (Priority 5)
- Email: "Weekly newsletter" → **IGNORE** (Priority 1)

### 3. Safety Guardrails System
Three-tier action classification to prevent accidents:

- **GREEN**: Safe to auto-execute (read email, search memory, fetch calendar)
- **YELLOW**: Requires your approval (draft email, create calendar event, delete memory)
- **RED**: Blocked entirely (send email, delete email, delete calendar event)

This ensures AURA never takes destructive or irreversible actions without permission.

### 4. Orchestrator Agent
Routes your natural language input to the right specialized agent:

- Detects intent: "Remember that..." → Memory Agent (store)
- "What do you know about..." → Memory Agent (search)
- "I want to achieve..." → Goal Agent (future)
- Uses local Gemma for classification, escalates complex queries to cloud Gemini

### 5. FastAPI Backend (Partial)
REST API with endpoints for:
- `/chat` - Send messages to orchestrator
- `/health` - System health check
- `/logs` - View agent activity logs

---

## Tech Stack

### AI Models
- **Gemma 4 E2B (Local)**: 7.2GB quantized model via Ollama
  - Used for: Simple classification, routine queries (speed not critical)
  - Cost: Free (runs on your machine)
  - Privacy: 100% local, no data sent to cloud
  
- **Gemini 3.5 Flash (Cloud)**: Google AI API
  - Used for: Email triage, complex reasoning, goal decomposition, time-sensitive tasks
  - Cost: ~$0.50/year (only called when needed)
  - Speed: <1 second per request (vs 5-10s local)

### Backend Stack
- **Python 3.11+**: Core runtime
- **LangGraph 0.2.x**: Multi-agent orchestration framework
- **FastAPI**: REST API server
- **ChromaDB 0.5.x**: Vector database for semantic memory search
- **SQLite**: Structured metadata storage with FTS5 keyword search
- **pytest**: Testing framework (57 tests passing, 91% coverage)

### Integrations
- **Gmail API**: OAuth 2.0 authentication with token refresh
- **Google Calendar API**: Coming in Week 6
- **Tavily API**: Web search (planned)

---

## Quick Start

### Prerequisites
- **Python 3.11+**
- **Ollama** (for local Gemma model): [https://ollama.ai](https://ollama.ai)
- **Google AI Studio API key**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **Conda** (recommended for Python environment)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/aura.git
cd aura

# 2. Install Ollama and pull Gemma 4 E2B model (7.2GB)
ollama pull gemma4:e2b

# 3. Create Python environment
conda create -n aura python=3.11
conda activate aura

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Configure environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Optional: Gmail Setup

To enable email triage, you need OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "aura-test")
3. Navigate to **APIs & Services → Library**
4. Enable **Gmail API**
5. Go to **APIs & Services → Credentials**
6. Click **Create Credentials → OAuth client ID**
7. Choose **Desktop app**, download JSON
8. Save as `./credentials/gmail_credentials.json`
9. Go to **OAuth consent screen → Test users**
10. Add your email address as a test user

### Verify Installation

```bash
# Start Ollama (if not already running)
ollama serve

# Run all tests (should see 57 tests pass)
pytest backend/tests/ -v --cov=backend

# Test Ollama connectivity
python tools/test_ollama.py

# Test Gmail OAuth (requires credentials setup)
python tools/test_gmail_auth.py

# Test email triage with real emails (requires Ollama + Gmail)
python tools/test_email_triage_live.py
```

---

## Project Structure

```
aura/
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py      # Routes user input to specialized agents
│   │   ├── memory_agent.py      # Stores and retrieves memories
│   │   └── email_triage.py      # Classifies and prioritizes emails
│   ├── memory/
│   │   └── store.py             # ChromaDB + SQLite memory storage
│   ├── integrations/
│   │   └── gmail.py             # Gmail API OAuth client
│   ├── guardrails/
│   │   └── rules.py             # Green/Yellow/Red action rules
│   ├── models/
│   │   ├── local.py             # Ollama (Gemma) client
│   │   └── cloud.py             # Gemini API client
│   ├── api/
│   │   └── main.py              # FastAPI server
│   └── tests/                   # 57 tests, 91% coverage
├── tools/
│   ├── validate_tool_calling.py # Week 1 validation (82.5% pass)
│   ├── test_gmail_auth.py       # Gmail OAuth test
│   └── test_email_triage_live.py # Live email classification
├── docs/
│   ├── architecture.md          # System architecture
│   └── week2-memory-system-explained.md
├── credentials/                 # OAuth tokens (gitignored)
├── data/                        # Memory database (gitignored)
└── .env                         # API keys (gitignored)
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User Input                        │
│            (Natural Language / API Call)            │
└───────────────────┬─────────────────────────────────┘
                    ↓
        ┌───────────────────────┐
        │  Orchestrator Agent   │
        │ (Intent Classification)│
        │   Gemma E2B (local)   │
        └───────────┬───────────┘
                    ↓
    ┌───────────────┼───────────────┬─────────────┐
    ↓               ↓               ↓             ↓
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Memory  │  │  Email   │  │   Goal   │  │ Research │
│  Agent  │  │  Triage  │  │  Agent   │  │  Agent   │
│         │  │          │  │ (future) │  │ (future) │
└────┬────┘  └────┬─────┘  └──────────┘  └──────────┘
     ↓            ↓
┌─────────┐  ┌─────────┐
│ChromaDB │  │  Gmail  │
│ SQLite  │  │   API   │
└─────────┘  └─────────┘
                    ↓
            ┌──────────────┐
            │  Guardrails  │
            │  (G / Y / R) │
            └──────┬───────┘
                   ↓
         Execute or Queue for Approval
```

**Flow:**
1. User sends natural language input via API or scheduled task
2. Orchestrator classifies intent (store_memory, search_memory, email_triage, etc.)
3. Routes to appropriate specialized agent
4. Agent executes action through integrations (Gmail API, memory store)
5. Guardrails check if action is safe (green), needs approval (yellow), or blocked (red)
6. Result returned to user with reasoning

---

## Development Timeline

**22 weeks total** (5 weeks complete)

### Phase 1: Foundation (Weeks 1-5) - COMPLETE
- Multi-agent orchestration with LangGraph
- Persistent memory with semantic search
- Gmail integration with AI triage
- Safety guardrails system
- FastAPI backend

### Phase 2: Calendar & Goals (Weeks 6-9) - IN PROGRESS
- Google Calendar integration
- Morning brief generation
- Goal tracking and decomposition
- Adaptive replanning

### Phase 3: Intelligence (Weeks 10-13)
- Web search integration
- Research agent
- Multi-source information synthesis

### Phase 4: Dashboard (Weeks 14-17)
- React frontend
- Real-time WebSocket updates
- Agent activity visualization
- Approval queue UI

### Phase 5: Autonomy (Weeks 18-21)
- Scheduled heartbeat tasks
- Morning brief automation
- Night summary generation
- Battery-aware scheduling

### Phase 6: Launch (Week 22)
- Security audit
- Documentation polish
- Performance optimization
- Public release

---

## Contributing

This is an active development project. See [CLAUDE.md](CLAUDE.md) for:
- Development environment setup
- Coding standards
- Architecture decisions
- Week-by-week progress

---

## License

MIT
