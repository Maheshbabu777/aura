# AURA

Personal AI Operating System - A local-first, cloud-hybrid AI system for autonomous task management and goal tracking.

## Overview

AURA is a multi-agent AI system built with LangGraph that combines local inference (Gemma 4 E2B) with cloud reasoning (Gemini 3 Flash) for privacy-conscious autonomous operation. The system features persistent memory with staleness detection, long-horizon goal tracking with adaptive replanning, and transparent action logging through a real-time dashboard.

## Core Architecture

- **Agent Layer**: LangGraph-based multi-agent coordination with explicit state management
- **Local Model**: Gemma 4 E2B (7.2 GB) via Ollama for routine operations
- **Cloud Reasoning**: Gemini 3 Flash for complex goal decomposition and planning
- **Memory System**: ChromaDB vector store with SQLite FTS5 keyword fallback and Fernet encryption
- **API Layer**: FastAPI with WebSocket support for real-time agent activity streaming
- **Frontend**: React dashboard with live agent action visibility

## Current Status

Week 0: Environment Setup - Complete

## Prerequisites

- Python 3.11 or higher
- Ollama (https://ollama.ai)
- Google AI Studio API key (https://aistudio.google.com/app/apikey)

## Setup

```bash
# Pull local model
ollama pull gemma4:e2b

# Configure environment
cp .env.example .env
# Add your GEMINI_API_KEY to .env
```

## Planned Features

- Persistent vector memory with encryption and staleness detection
- Long-horizon goal decomposition with adaptive replanning
- Gmail and Google Calendar integration via MCP servers with direct API fallbacks
- Three-tier action classification (Green/Yellow/Red) with approval queue
- Autonomous heartbeat service with battery-aware scheduling
- Complete audit trail with reasoning logs

## Development Timeline

25 weeks total across 6 phases:
- Phase 1 (Weeks 1-5): Foundation - Memory agent and orchestrator
- Phase 2 (Weeks 6-9): Integrations - Gmail, Calendar, guardrails
- Phase 3 (Weeks 10-13): Goal tracking and replanning
- Phase 4 (Weeks 14-17): React dashboard
- Phase 5 (Weeks 18-21): Autonomous heartbeat
- Phase 6 (Weeks 22-25): Security, documentation, launch

## License

MIT
