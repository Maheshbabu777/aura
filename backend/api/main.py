"""
FastAPI application for AURA backend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from pathlib import Path
from loguru import logger

from backend.agents.orchestrator import OrchestratorAgent
from backend.config.settings import settings
from backend.api.routers import heartbeat, actions


# Configure logging
log_file = Path("./logs/aura.log")
log_file.parent.mkdir(parents=True, exist_ok=True)

logger.add(
    log_file,
    rotation="10 MB",
    retention="7 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
)


# Initialize FastAPI app
app = FastAPI(
    title="AURA API",
    description="Personal AI Operating System API",
    version="0.1.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(heartbeat.router)
app.include_router(actions.router)


# Initialize orchestrator (singleton)
orchestrator = OrchestratorAgent()


# Request/Response models
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    success: bool
    message: str
    intent: str
    agent: str
    metadata: Dict[str, Any] = {}


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("AURA backend starting up")
    logger.info(f"Ollama: {settings.ollama_base_url} | Model: {settings.ollama_model}")
    logger.info(f"Gemini: {settings.gemini_model}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("AURA backend shutting down")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "AURA API",
        "version": "0.1.0",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint: routes user message through orchestrator.

    Args:
        request: ChatRequest with user message

    Returns:
        ChatResponse with agent's response and metadata
    """
    try:
        logger.info(f"Chat request: {request.message[:100]}...")

        # Route through orchestrator
        result = orchestrator.route(request.message)

        return ChatResponse(
            success=result["success"],
            message=result["message"],
            intent=result["intent"],
            agent=result["agent"],
            metadata=result.get("classification", {}),
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs")
async def get_logs(lines: int = 100):
    """
    Get recent log entries.

    Args:
        lines: Number of recent lines to return (default: 100)

    Returns:
        Dict with log entries
    """
    try:
        log_file = Path("./logs/aura.log")

        if not log_file.exists():
            return {"logs": [], "message": "No log file found"}

        # Read last N lines
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "logs": [line.strip() for line in recent_lines],
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
        }

    except Exception as e:
        logger.error(f"Logs endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    Detailed health check: verify all components.

    Returns:
        Health status of all services
    """
    health_status = {
        "api": "healthy",
        "ollama": "unknown",
        "gemini": "unknown",
        "memory": "unknown",
    }

    # Test Ollama
    try:
        from backend.models.local import ollama_client

        test_response = ollama_client.generate("ping", temperature=0.1, max_tokens=10)
        health_status["ollama"] = "healthy" if test_response else "degraded"
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        health_status["ollama"] = "unhealthy"

    # Test Gemini (skip to avoid unnecessary API calls)
    health_status["gemini"] = "not_tested"

    # Test Memory
    try:
        from backend.agents.memory_agent import MemoryAgent

        mem_agent = MemoryAgent()
        # Just check if we can instantiate
        health_status["memory"] = "healthy"
    except Exception as e:
        logger.warning(f"Memory health check failed: {e}")
        health_status["memory"] = "unhealthy"

    return health_status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
