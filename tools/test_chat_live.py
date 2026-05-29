"""
Interactive test script for the AURA Chat Engine.

Session is managed server-side — the client just sends messages.
The server tracks history, active agents, and sticky routing internally.
"""

import sys
import os
import asyncio
from rich.console import Console

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routers.chat import chat, ChatRequest
from backend.memory.activity_stream import activity_stream

console = Console()

async def main():
    console.print("\n[bold blue]=== AURA Chat Interface Test ===[/bold blue]")
    
    # Inject some fake events into the activity stream
    console.print("[dim]Injecting fake events into Activity Stream for testing...[/dim]")
    activity_stream.log("GoalAgent", "Completed Task: Watch PyTorch Tutorial")
    activity_stream.log("EmailTriage", "Archived 3 promotional emails")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if user_input.lower() == 'reset':
                from backend.agents.orchestrator import orchestrator
                orchestrator.session.reset()
                console.print("[dim]Session reset.[/dim]")
                continue
                
            console.print("[dim]AURA is thinking...[/dim]")
            
            # Call the Chat API — no history needed, server manages it
            req = ChatRequest(message=user_input)
            response = await chat(req)
            
            # Print response
            console.print(f"\n[bold green]AURA:[/bold green] {response.message}")
            
            # If there are suggested actions, print them
            if response.data and response.data.get("suggested_actions"):
                console.print("\n[bold yellow]Suggested Actions:[/bold yellow]")
                for i, action in enumerate(response.data["suggested_actions"], 1):
                    console.print(f"  [yellow]{i}.[/yellow] {action}")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
