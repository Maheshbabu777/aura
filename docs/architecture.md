# AURA Architecture Documentation

**Version**: 0.1.0  
**Last Updated**: 2026-05-26  
**Status**: Week 4 Complete

---

## Overview

AURA is a privacy-first, autonomous personal AI assistant built on a multi-agent architecture. It uses LangGraph for agent orchestration, local models (Gemma 4 E4B) for routine tasks, and cloud models (Gemini 3 Flash) for complex reasoning.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Orchestrator Agent (Router)                │   │
│  │  - Intent classification (local/cloud)               │   │
│  │  - Routes to specialized agents                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                    │
│         ┌────────────────┼────────────────┐                 │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌───────────┐    ┌──────────┐    ┌──────────┐            │
│  │  Memory   │    │   Goal   │    │   Task   │            │
│  │  Agent    │    │  Agent   │    │  Agent   │            │
│  │ (Week 2)  │    │(Week 9+) │    │(Week 5+) │            │
│  └───────────┘    └──────────┘    └──────────┘            │
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
                  Google Gemini API
                 (Complex reasoning)
```

---

## Components

### 1. Orchestrator Agent

**Location**: `backend/agents/orchestrator.py`  
**Purpose**: Routes user input to appropriate specialized agents based on intent classification.

**Intent Types**:
- `store_memory` - Save information to memory
- `retrieve_memory` - Get stored information
- `search_memory` - Find related memories
- `update_memory` - Modify existing memories
- `goal_request` - Goal tracking (not implemented)
- `task_request` - API actions (not implemented)
- `general_chat` - Conversational responses

**Classification Strategy**:
- Uses local model (Gemma E4B) for routine classification
- Escalates to cloud model (Gemini 3 Flash) for complex intents
- Parses structured response format:
  ```
  INTENT: <intent_name>
  AGENT: <agent_name>
  ENTITIES: <extracted entities>
  REASONING: <brief explanation>
  ```

**Key Methods**:
- `classify_intent()` - Classify user message using local or cloud model
- `route()` - Main routing logic to appropriate agent
- `_parse_classification()` - Parse model response into structured dict
- `_route_to_memory_agent()` - Handle memory-related requests
- `_handle_general_chat()` - Handle conversational messages

---

### 2. Memory Agent

**Location**: `backend/agents/memory_agent.py`  
**Purpose**: Manages persistent memory using ChromaDB + SQLite dual-database architecture.

**Capabilities**:
- Store memories with auto entity classification
- Semantic search using embeddings
- Update existing memories
- Delete memories
- Staleness detection (TTL-based)
- Memory tagging and deduplication
- Priority scoring

**Features** (Week 2 + Week 3):
- Smart explicit intent detection
- Entity types: Person/Goal/Job/Location/Fact
- Tags with auto-tagging from content
- Deduplication using similarity threshold
- Priority scoring (importance + recency + access frequency)
- Access tracking

---

### 3. Memory Store

**Location**: `backend/memory/store.py`  
**Purpose**: Low-level storage abstraction over ChromaDB + SQLite.

**Dual-Database Design**:
- **ChromaDB**: Semantic search via embeddings
  - Model: `sentence-transformers/all-MiniLM-L6-v2`
  - Collection: `memories`
  - Query: cosine similarity search
  
- **SQLite**: Structured queries + full-text search
  - Schema: id, text, entity_type, created_at, updated_at, ttl_days, tags, access_count, last_accessed_at, importance, metadata
  - FTS5: Full-text search on text column
  - Audit trail for all operations

**Key Methods**:
- `write_memory()` - Store new memory
- `search_memory()` - Semantic search
- `update_memory()` - Modify existing memory
- `get_memory()` - Retrieve by ID with optional access tracking
- `delete_memory()` - Remove memory
- `is_stale()` - Check if memory past TTL
- `get_stale_memories()` - Find all stale memories
- `find_duplicates()` - Detect similar memories
- `merge_memories()` - Combine duplicate memories
- `calculate_priority_score()` - Multi-factor scoring (0-100)
- `get_prioritized_memories()` - Retrieve by priority

---

### 4. Model Clients

#### Local Model Client

**Location**: `backend/models/local.py`  
**Model**: Gemma 4 E4B via Ollama  
**Use Cases**: Intent classification, routine tasks, tool calling

**Methods**:
- `generate()` - Text completion
- `chat()` - Multi-turn conversation

#### Cloud Model Client

**Location**: `backend/models/cloud.py`  
**Model**: Gemini 3 Flash (Google AI API)  
**Use Cases**: Complex reasoning, goal decomposition, brief generation

**Features**:
- Token usage logging for cost tracking
- System instruction support
- Generation config (temperature, max_tokens)

---

### 5. FastAPI Backend

**Location**: `backend/api/main.py`  
**Purpose**: HTTP API server with WebSocket support (future)

**Endpoints**:

- `GET /` - Health check
  - Returns: service status and version
  
- `POST /chat` - Main chat endpoint
  - Request: `{"message": "user text"}`
  - Response: `{"success": bool, "message": str, "intent": str, "agent": str, "metadata": {}}`
  - Routes through orchestrator → appropriate agent → return response
  
- `GET /logs?lines=N` - Get recent log entries
  - Returns: Last N lines from `logs/aura.log`
  - Default: 100 lines
  
- `GET /health` - Detailed health check
  - Tests: API, Ollama, Gemini, Memory
  - Returns: health status for each component

**Middleware**:
- CORS: Allows frontend requests
- Logging: Structured JSON logs with loguru
- Startup: Initializes orchestrator, logs configuration

---

### 6. Configuration

**Location**: `backend/config/settings.py`  
**Purpose**: Centralized configuration using Pydantic and python-dotenv

**Settings**:
- `ollama_base_url` - Ollama API endpoint
- `ollama_model` - Local model name
- `gemini_api_key` - Google AI API key
- `gemini_model` - Cloud model name
- `memory_db_path` - ChromaDB directory
- `audit_log_path` - SQLite database path
- `log_level` - Logging verbosity

**Environment Variables** (`.env`):
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
GEMINI_API_KEY=<your-key>
GEMINI_MODEL=gemini-1.5-flash
LOG_LEVEL=INFO
```

---

### 7. Prompts

**Location**: `backend/prompts/`  
**Format**: Plain text files loaded at runtime

**Files**:
- `orchestrator.txt` - Intent classification instructions
- `memory_agent.txt` - (future) Memory agent system prompt
- `goal_agent.txt` - (future) Goal tracking prompt
- `email_triage.txt` - (future) Email classification prompt

**Design Philosophy**:
- Prompts never hardcoded in Python
- Loaded at runtime for easy iteration
- Version-controlled with code
- Clear, structured format for model responses

---

## Data Flow

### Example: Store Memory Request

```
1. User: "Remember that I work at TechCorp"
   ↓
2. FastAPI /chat endpoint receives request
   ↓
3. Orchestrator.route() called
   ↓
4. Orchestrator.classify_intent() using Gemma
   → Response: "INTENT: store_memory, AGENT: memory_agent"
   ↓
5. Orchestrator._route_to_memory_agent()
   ↓
6. MemoryAgent.process() with smart intent detection
   ↓
7. MemoryAgent._execute_store()
   ↓
8. MemoryStore.write_memory()
   → ChromaDB: Store embedding
   → SQLite: Store metadata
   ↓
9. Return: "Remembered: I work at TechCorp"
   ↓
10. FastAPI returns JSON response to user
```

---

## Testing Strategy

### Unit Tests
- `test_memory_store.py` - MemoryStore CRUD operations
- `test_memory_agent.py` - MemoryAgent intent detection
- `test_orchestrator.py` - Orchestrator routing logic
- `test_memory_staleness.py` - TTL-based staleness
- `test_memory_tagging.py` - Tagging and search
- `test_memory_deduplication.py` - Similarity detection
- `test_memory_prioritization.py` - Priority scoring

### Integration Tests
- `tools/test_orchestrator.py` - End-to-end orchestrator flow
- `tools/test_api.py` - FastAPI endpoints

### Coverage
- **Current**: 91% on `backend/agents/` and `backend/memory/`
- **Target**: >70% by Week 22
- **Decision Gate**: >50% required for Week 4 → Week 5 transition ✅

---

## Deployment

### Development
```bash
# Start Ollama (if not running)
ollama serve

# Activate environment
conda activate tf-gpu

# Start FastAPI server
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal: test endpoints
python tools/test_api.py
```

### Production (Future)
- Docker Compose: backend + frontend + Ollama
- Systemd service for autonomous operation
- Log rotation with loguru
- Health monitoring

---

## Security Considerations

### Current
- API keys in `.env` file (never committed)
- CORS restricted to localhost:3000 and localhost:5173
- No authentication (single-user, local deployment)
- Structured logging (no secrets logged)

### Future (Week 20)
- Rate limiting with slowapi
- Input validation with Pydantic
- Audit log for all actions
- Security scan with bandit

---

## Performance Characteristics

### Measured (Week 4)
- Memory store init: ~2 seconds (embedding model load)
- Intent classification (Gemma): ~30 seconds (includes model load)
- Memory search: <1 second
- API response time: <35 seconds (with model loading)

### Targets (Week 21)
- Morning brief: <10 seconds
- Email triage (10 emails): <15 seconds
- Memory search: <500ms (p95)
- Peak RAM: <7GB

---

## Dependencies

### Core
- `langgraph` - Multi-agent orchestration
- `fastapi` - API server
- `uvicorn` - ASGI server
- `chromadb` - Vector database
- `sqlite3` - Metadata storage
- `loguru` - Structured logging
- `pydantic` - Data validation
- `python-dotenv` - Environment configuration

### AI Models
- `requests` - Ollama HTTP client
- `google-generativeai` - Gemini API client
- `sentence-transformers` - Embedding model (via ChromaDB)

### Testing
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `unittest.mock` - Mocking for unit tests

---

## Future Architecture

### Phase 2: Integrations (Weeks 5-8)
- Gmail API integration
- Google Calendar API integration
- Email triage agent
- Follow-up tracker

### Phase 3: Goal Tracking (Weeks 9-11)
- Goal Agent with adaptive replanning
- Milestone decomposition
- Progress monitoring
- Night summary generation

### Phase 4: Dashboard (Weeks 12-15)
- React frontend
- WebSocket for real-time updates
- Memory browser UI
- Goal tracker UI
- Approval queue UI

### Phase 5: Autonomous Operation (Weeks 16-19)
- APScheduler heartbeat tasks
- Morning brief (8 AM)
- Email check (every 2 hours)
- Night summary (10 PM)
- Missed job recovery

---

## Design Decisions

### Why Dual-Database (ChromaDB + SQLite)?
- ChromaDB: Best for semantic search via embeddings
- SQLite: Best for structured queries, FTS5, audit logs
- Both: Redundancy ensures data durability

### Why Local-First with Cloud Escalation?
- Privacy: Most data never leaves machine
- Cost: ~$0.24/year vs. cloud-only APIs
- Performance: Local model responds in seconds
- Reliability: Works offline with degraded mode

### Why LangGraph over LangChain?
- Better multi-agent orchestration
- Graph-based state management
- Easier agent composition
- Built for production use

---

## Appendix

### File Structure
```
backend/
├── agents/
│   ├── orchestrator.py       # Intent classification and routing
│   └── memory_agent.py       # Memory management
├── memory/
│   └── store.py              # ChromaDB + SQLite wrapper
├── models/
│   ├── local.py              # Ollama client
│   └── cloud.py              # Gemini client
├── api/
│   └── main.py               # FastAPI app
├── config/
│   └── settings.py           # Pydantic configuration
├── prompts/
│   └── orchestrator.txt      # System prompts
└── tests/
    ├── test_orchestrator.py
    ├── test_memory_agent.py
    ├── test_memory_store.py
    └── ... (Week 3 tests)
```

### Key Metrics (Week 4)
- Total tests: 93
- Test coverage: 91%
- Lines of code: ~1500 (agents + memory + api)
- API endpoints: 4
- Agents: 2 (orchestrator, memory)
- Storage: 2 (ChromaDB, SQLite)
- Models: 2 (Gemma local, Gemini cloud)

---

**Status**: Week 4 Complete ✅  
**Next**: Week 5 - Gmail Integration + Email Triage
