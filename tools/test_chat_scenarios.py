"""
Automated scenario testing script for AURA Chat Engine.
Tests a sequence of 4 questions covering memory, status, follow-up, and contextual queries.
"""

import asyncio
import sys
import os
from rich.console import Console

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routers.chat import chat, ChatRequest
from backend.agents.orchestrator import orchestrator
from backend.memory.activity_stream import activity_stream

console = Console()

async def run_scenario():
    console.print("\n[bold blue]=== Starting Automated Conversation Scenario Test ===[/bold blue]")
    
    # 1. Reset Session
    orchestrator.session.reset()
    console.print("[dim]Session reset.[/dim]")
    
    # Inject some fake events into the activity stream
    console.print("[dim]Injecting activity logs...[/dim]")
    activity_stream.log("GoalAgent", "Completed Task: Watch Rust Lifetimes Tutorial")
    activity_stream.log("EmailTriage", "Archived 5 promotional emails")
    
    # Define questions to test
    questions = [
        # Case 1: One-shot Memory Storage (should not trigger sticky routing lock)
        "Remember that my favourite programming language is Rust.",
        
        # Case 2: Status Request (triggers StatusAgent and sets sticky lock to conversational)
        "Give me my status report for today.",
        
        # Case 3: Follow-up Question (should use sticky routing & context to understand "fastest task")
        "Which of those actions is fastest to complete?",
        
        # Case 4: Contextual Memory Query (should refer to turn 1 using conversation history)
        "What did I say my favourite language was?"
    ]
    
    for i, question in enumerate(questions, 1):
        console.print(f"\n[bold cyan]Step {i} | User:[/bold cyan] {question}")
        console.print("[dim]AURA is thinking...[/dim]")
        
        try:
            req = ChatRequest(message=question)
            response = await chat(req)
            
            console.print(f"[bold green]AURA Response:[/bold green] {response.message}")
            console.print(f"[dim]Routed to: {response.agent} | Intent: {response.intent} | Active Agent Lock: {orchestrator.session.active_agent}[/dim]")
            
            if response.data and response.data.get("suggested_actions"):
                console.print("[bold yellow]Suggested Actions:[/bold yellow]")
                for action in response.data["suggested_actions"]:
                    console.print(f"  - {action}")
                    
        except Exception as e:
            console.print(f"[bold red]Error in Step {i}:[/bold red] {e}")
            
    console.print("\n[bold blue]=== Scenario Test Complete ===[/bold blue]")

if __name__ == "__main__":
    asyncio.run(run_scenario())
