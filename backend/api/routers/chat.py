from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

from backend.agents.orchestrator import orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None  # Kept for API compat; server manages state

class ChatResponse(BaseModel):
    success: bool
    message: str
    intent: Optional[str] = None
    agent: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main entry point for conversational interaction with AURA.

    Session management:
    - Server-side session tracks full conversation history
    - Server-side sticky routing prevents misclassification of follow-ups
    - The client does NOT need to send history; the server maintains it
    """
    try:
        session = orchestrator.session

        # ── 1. Add user message to session ──────────────────────────────
        session.add_user_message(request.message)

        # ── 2. Route through orchestrator ───────────────────────────────
        routing_result = orchestrator.route(request.message)

        # ── 3. Handle async status agent intercept ──────────────────────
        if (routing_result.get("agent") == "status_agent"
                and routing_result.get("message") == "[INTERCEPT_STATUS_REQUEST]"):
            from backend.agents.status_agent import status_agent

            # Pass full conversation history to status agent
            status_data = await status_agent.get_daily_status(
                chat_history=session.get_full_history()
            )

            response_message = status_data.get("summary_text", "Here is your status update.")

            # Save response to session and set sticky routing
            session.add_assistant_message(response_message)
            session.set_active_agent("conversational")

            return ChatResponse(
                success=True,
                message=response_message,
                intent="status_request",
                agent="status_agent",
                data={"suggested_actions": status_data.get("suggested_actions", [])},
                metadata={"intent": "status_request", "agent": "status_agent"},
            )

        # ── 3b. Handle async background research agent intercept ────────
        if (routing_result.get("agent") == "research_agent"
                and routing_result.get("message") == "[INTERCEPT_RESEARCH_REQUEST]"):
            from backend.agents.research_agent import research_agent

            # Spawn the agent in the background WITHOUT awaiting it
            asyncio.create_task(research_agent.run(request.message))

            response_message = "I've spun up a sub-agent to research this in the background. I'll inject the results into our conversation when it's done."

            # Save the fast-return response to session
            session.add_assistant_message(response_message)
            
            # Do NOT set sticky routing, because the user should be able to chat normally
            # while the agent works in the background.
            session.clear_active_agent()

            return ChatResponse(
                success=True,
                message=response_message,
                intent="research_request",
                agent="research_agent",
                metadata={
                    "intent": "research_request", 
                    "agent": "research_agent",
                    "is_agent_running": True  # UI Flag for the spinning wheel!
                },
            )

        # ── 4. Save response to session ─────────────────────────────────
        response_message = routing_result.get("message", "I couldn't process that.")
        session.add_assistant_message(response_message)

        # ── 5. Set sticky routing based on response type ────────────────
        intent = routing_result.get("intent", "")

        if intent in ("store_memory", "retrieve_memory", "search_memory", "update_memory"):
            # Memory operations are one-shot — don't lock routing
            session.clear_active_agent()
        elif routing_result.get("success", False):
            # Successful responses activate conversational follow-up mode
            session.set_active_agent("conversational")

        # ── 6. Return response ──────────────────────────────────────────
        return ChatResponse(
            success=routing_result.get("success", False),
            message=response_message,
            intent=routing_result.get("intent"),
            agent=routing_result.get("agent"),
            data=routing_result.get("data"),
            metadata=routing_result.get("classification"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
